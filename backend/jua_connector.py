import os

from dotenv import load_dotenv
from jua import JuaClient
from jua.errors.api_errors import (
    NotAuthenticatedError,
    RequestExceedsCreditLimitError,
    UnauthorizedError,
)
from jua.errors.jua_error import JuaError
from jua.settings import AuthenticationSettings, JuaSettings
from jua.types.geo import LatLon
from jua.weather import Models

load_dotenv()

DEFAULT_VARIABLES = [
    "wind_speed_at_height_level_10m",
    "air_temperature_at_height_level_2m",
    "precipitation_amount_at_surface",
]

# Severity thresholds
_WIND_SEVERE_KMH = 90
_WIND_MINOR_KMH = 60
_PRECIP_MINOR_MM_HR = 10
_TEMP_MINOR_K = 268


def authenticate() -> JuaClient:
    key_id = os.environ.get("JUA_KEY_ID")
    secret = os.environ.get("JUA_SECRET")
    if not key_id:
        raise ValueError("Missing required environment variable: JUA_KEY_ID")
    if not secret:
        raise ValueError("Missing required environment variable: JUA_SECRET")
    settings = JuaSettings(
        auth=AuthenticationSettings(api_key_id=key_id, api_key_secret=secret)
    )
    return JuaClient(settings=settings)


def _handle_sdk_error(exc: Exception, context: str) -> None:
    if isinstance(exc, NotAuthenticatedError):
        raise RuntimeError(
            f"Jua authentication failed ({context}): invalid or missing API credentials (HTTP 401). "
            "Check JUA_KEY_ID and JUA_SECRET."
        ) from exc
    if isinstance(exc, UnauthorizedError):
        raise RuntimeError(
            f"Jua request forbidden ({context}): account lacks access to this resource (HTTP 403)."
        ) from exc
    if isinstance(exc, RequestExceedsCreditLimitError):
        raise RuntimeError(
            f"Jua quota or billing issue ({context}): request exceeds credit limit (HTTP 400/402). "
            f"Details: {exc}"
        ) from exc
    if isinstance(exc, JuaError):
        msg = str(exc)
        if "400" in msg:
            raise RuntimeError(
                f"Jua bad request ({context}): malformed request parameters (HTTP 400). Details: {msg}"
            ) from exc
        if "402" in msg:
            raise RuntimeError(
                f"Jua payment required ({context}): quota or billing issue (HTTP 402). Details: {msg}"
            ) from exc
        raise RuntimeError(f"Jua API error ({context}): {msg}") from exc
    raise RuntimeError(f"Jua API error ({context}): {exc}") from exc


def get_forecast(
    lat: float, lon: float, variables: list[str], hours: int = 24
) -> dict:
    merged = list(dict.fromkeys(DEFAULT_VARIABLES + variables))
    client = authenticate()
    try:
        model = client.weather.get_model(Models.EPT2)
        dataset = model.get_forecasts(
            init_time="latest",
            variables=merged,
            points=[LatLon(lat=lat, lon=lon)],
            max_lead_time=hours,
        )
        return dataset.to_xarray().to_dict()
    except Exception as exc:
        _handle_sdk_error(exc, f"lat={lat}, lon={lon}")
    raise AssertionError("unreachable")


def get_regional_forecast(
    bbox: tuple[float, float, float, float], variables: list[str], hours: int = 24
) -> dict:
    if len(bbox) != 4:
        raise ValueError(
            f"bbox must be a 4-element tuple (min_lat, min_lon, max_lat, max_lon), got {len(bbox)} elements"
        )
    min_lat, min_lon, max_lat, max_lon = bbox
    merged = list(dict.fromkeys(DEFAULT_VARIABLES + variables))
    client = authenticate()
    try:
        model = client.weather.get_model(Models.EPT2)
        dataset = model.get_forecasts(
            init_time="latest",
            variables=merged,
            latitude=slice(min_lat, max_lat),
            longitude=slice(min_lon, max_lon),
            max_lead_time=hours,
        )
        return dataset.to_xarray().to_dict()
    except Exception as exc:
        _handle_sdk_error(exc, f"bbox={bbox}")
    raise AssertionError("unreachable")


def _classify_severity(conditions: dict) -> tuple[bool, str]:
    minor_flags = 0
    severe = False

    wind = conditions.get("wind_speed_at_height_level_10m")
    if wind is not None:
        if wind > _WIND_SEVERE_KMH:
            severe = True
        elif wind > _WIND_MINOR_KMH:
            minor_flags += 1

    precip = conditions.get("precipitation_amount_at_surface")
    if precip is not None and precip > _PRECIP_MINOR_MM_HR:
        minor_flags += 1

    temp = conditions.get("air_temperature_at_height_level_2m")
    if temp is not None and temp < _TEMP_MINOR_K:
        minor_flags += 1

    if severe:
        return True, "severe"
    if minor_flags >= 2:
        return True, "moderate"
    if minor_flags == 1:
        return True, "minor"
    return False, "ok"


def scan_route(
    waypoints: list[tuple[float, float]], variables: list[str], hours: int = 24
) -> list[dict]:
    if len(waypoints) < 5:
        raise ValueError(
            f"scan_route requires at least 5 waypoints, got {len(waypoints)}"
        )
    if len(waypoints) > 10:
        raise ValueError(
            f"scan_route accepts at most 10 waypoints, got {len(waypoints)}"
        )

    results = []
    for lat, lon in waypoints:
        try:
            forecast_data = get_forecast(lat, lon, variables, hours)
            # Extract peak values across the forecast horizon for each threshold variable
            conditions = _extract_peak_conditions(forecast_data)
            flagged, severity = _classify_severity(conditions)
            results.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "conditions": conditions,
                    "flagged": flagged,
                    "severity": severity,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "flagged": False,
                    "severity": "unknown",
                    "error": str(exc),
                }
            )

    return results


def _extract_peak_conditions(forecast_data: dict) -> dict:
    """Extract the worst-case (peak) value for each threshold variable from xarray dict output."""
    conditions = {}
    data_vars = forecast_data.get("data_vars", {})
    for var in DEFAULT_VARIABLES:
        if var in data_vars:
            var_data = data_vars[var].get("data")
            if var_data is not None:
                flat = _flatten(var_data)
                if flat:
                    # For temperature, worst case is minimum; for wind/precip, maximum
                    if var == "air_temperature_at_height_level_2m":
                        conditions[var] = min(flat)
                    else:
                        conditions[var] = max(flat)
    return conditions


def _flatten(nested) -> list:
    """Recursively flatten nested lists into a flat list of numbers."""
    if isinstance(nested, list):
        result = []
        for item in nested:
            result.extend(_flatten(item))
        return result
    if isinstance(nested, (int, float)) and not isinstance(nested, bool):
        return [nested]
    return []


# Example: Hamburg → Munich route scan (8 waypoints)
# authenticate()  # validates credentials on startup
# route = [(53.55,10.00),(53.20,10.40),(52.80,10.90),(52.40,11.50),(52.10,12.10),(51.60,12.40),(51.00,11.60),(48.14,11.58)]
# results = scan_route(route, variables=[], hours=24)
# print([{"lat":r["lat"],"lon":r["lon"],"severity":r["severity"]} for r in results])
