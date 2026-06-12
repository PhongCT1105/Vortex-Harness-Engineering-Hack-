# To switch from jua_connector: change 'from jua_connector import ...' to 'from open_meteo_connector import ...'

import math

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_VARIABLES = [
    "wind_speed_at_height_level_10m",
    "air_temperature_at_height_level_2m",
    "precipitation_amount_at_surface",
]

# Jua variable name → Open-Meteo variable name
VARIABLE_MAP = {
    "wind_speed_at_height_level_10m": "windspeed_10m",
    "air_temperature_at_height_level_2m": "temperature_2m",
    "precipitation_amount_at_surface": "precipitation",
}

# Severity thresholds — identical to jua_connector.py
_WIND_SEVERE_KMH = 90
_WIND_MINOR_KMH = 60
_PRECIP_MINOR_MM_HR = 10
_TEMP_MINOR_K = 268


def _handle_http_error(response: requests.Response, context: str) -> None:
    status = response.status_code
    if status == 400:
        raise RuntimeError(
            f"Open-Meteo bad request ({context}): malformed request parameters (HTTP 400). "
            f"Details: {response.text}"
        )
    if status == 404:
        raise RuntimeError(
            f"Open-Meteo endpoint not found ({context}): check BASE_URL (HTTP 404)."
        )
    if status == 429:
        raise RuntimeError(
            f"Open-Meteo rate limit exceeded ({context}): too many requests (HTTP 429). "
            "Wait before retrying."
        )
    if status >= 500:
        raise RuntimeError(
            f"Open-Meteo server error ({context}): HTTP {status}. Try again later."
        )
    raise RuntimeError(
        f"Open-Meteo unexpected error ({context}): HTTP {status}. Details: {response.text}"
    )


def get_forecast(
    lat: float, lon: float, variables: list[str], hours: int = 24
) -> dict:
    merged = list(dict.fromkeys(DEFAULT_VARIABLES + variables))
    om_vars = [VARIABLE_MAP.get(v, v) for v in merged]
    # Open-Meteo free tier supports up to 16 forecast days
    forecast_days = min(max(1, math.ceil(hours / 24)), 16)

    try:
        response = requests.get(
            BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": ",".join(om_vars),
                "forecast_days": forecast_days,
                "wind_speed_unit": "kmh",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Open-Meteo network error (lat={lat}, lon={lon}): {exc}"
        ) from exc

    if not response.ok:
        _handle_http_error(response, f"lat={lat}, lon={lon}")

    data = response.json()
    hourly = data.get("hourly", {})

    result = {"data_vars": {}}
    for jua_var in merged:
        om_var = VARIABLE_MAP.get(jua_var, jua_var)
        values = hourly.get(om_var, [])
        # Slice to requested hours; filter out None
        values = [v for v in values[:hours] if v is not None]
        if not values:
            continue
        if jua_var == "air_temperature_at_height_level_2m":
            # Open-Meteo returns °C; convert to K and take minimum (worst case)
            values_k = [v + 273.15 for v in values]
            result["data_vars"][jua_var] = {"data": min(values_k)}
        elif jua_var == "wind_speed_at_height_level_10m":
            result["data_vars"][jua_var] = {"data": max(values)}
        else:
            result["data_vars"][jua_var] = {"data": max(values)}

    return result


def get_regional_forecast(
    bbox: tuple[float, float, float, float], variables: list[str], hours: int = 24
) -> dict:
    if len(bbox) != 4:
        raise ValueError(
            f"bbox must be a 4-element tuple (min_lat, min_lon, max_lat, max_lon), "
            f"got {len(bbox)} elements"
        )
    min_lat, min_lon, max_lat, max_lon = bbox
    corners = [
        (min_lat, min_lon),
        (min_lat, max_lon),
        (max_lat, min_lon),
        (max_lat, max_lon),
    ]

    corner_results = []
    for lat, lon in corners:
        result = get_forecast(lat, lon, variables, hours)
        corner_results.append(result)

    # Average each variable's peak value across the 4 corners
    merged = list(dict.fromkeys(DEFAULT_VARIABLES + variables))
    averaged = {"data_vars": {}}
    for jua_var in merged:
        values = [
            r["data_vars"][jua_var]["data"]
            for r in corner_results
            if jua_var in r["data_vars"]
        ]
        # Only average when all corners returned data; skip partial results
        if len(values) == len(corner_results):
            averaged["data_vars"][jua_var] = {"data": sum(values) / len(values)}

    return averaged


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
            conditions = {
                var: forecast_data["data_vars"][var]["data"]
                for var in DEFAULT_VARIABLES
                if var in forecast_data["data_vars"]
            }
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
