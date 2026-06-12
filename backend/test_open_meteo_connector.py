"""
Comprehensive unit tests for open_meteo_connector.py

Run with:
    python3 -m pytest test_open_meteo_connector.py -v
"""

import math
from unittest.mock import MagicMock, patch, call

import pytest

import open_meteo_connector as omc
from open_meteo_connector import (
    DEFAULT_VARIABLES,
    VARIABLE_MAP,
    _classify_severity,
    _handle_http_error,
    get_forecast,
    get_regional_forecast,
    scan_route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_om_response(wind_kmh: float, temp_c: float, precip_mm: float, hours: int = 24) -> dict:
    """
    Build a realistic Open-Meteo JSON response dict.
    The response contains hourly arrays of length `hours` with the given
    constant values (simulating a flat forecast for easy assertion).
    """
    return {
        "latitude": 37.77,
        "longitude": -122.41,
        "hourly": {
            "windspeed_10m": [wind_kmh] * hours,
            "temperature_2m": [temp_c] * hours,
            "precipitation": [precip_mm] * hours,
        },
    }


def make_mock_response(json_data: dict, status_code: int = 200, text: str = "") -> MagicMock:
    """Return a mock requests.Response with .ok, .status_code, .json(), .text set."""
    mock = MagicMock()
    mock.ok = status_code < 400
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.text = text
    return mock


# ---------------------------------------------------------------------------
# TestHandleHttpError
# ---------------------------------------------------------------------------

class TestHandleHttpError:
    """Tests for _handle_http_error covering every documented status code."""

    def _make_resp(self, status_code: int, text: str = "err") -> MagicMock:
        r = MagicMock()
        r.status_code = status_code
        r.text = text
        return r

    def test_400_raises_with_bad_request_message(self):
        r = self._make_resp(400, "bad param")
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        msg = str(exc_info.value)
        assert "400" in msg
        assert "bad param" in msg

    def test_404_raises_with_not_found_message(self):
        r = self._make_resp(404)
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        assert "404" in str(exc_info.value)

    def test_429_raises_with_rate_limit_message(self):
        r = self._make_resp(429)
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        msg = str(exc_info.value)
        assert "429" in msg or "rate limit" in msg.lower()

    def test_500_raises_server_error(self):
        r = self._make_resp(500)
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        msg = str(exc_info.value)
        assert "500" in msg

    def test_503_raises_server_error(self):
        r = self._make_resp(503)
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        msg = str(exc_info.value)
        assert "503" in msg

    def test_418_raises_unexpected_error(self):
        """418 I'm a Teapot — should fall through to the generic handler."""
        r = self._make_resp(418, "teapot")
        with pytest.raises(RuntimeError) as exc_info:
            _handle_http_error(r, "test-context")
        msg = str(exc_info.value)
        assert "418" in msg

    def test_context_string_appears_in_error(self):
        """The context string passed in should appear in every error message."""
        for code in [400, 404, 429, 500, 418]:
            r = self._make_resp(code)
            with pytest.raises(RuntimeError) as exc_info:
                _handle_http_error(r, "my-special-context")
            assert "my-special-context" in str(exc_info.value), (
                f"Context missing from error for status {code}"
            )


# ---------------------------------------------------------------------------
# TestGetForecast
# ---------------------------------------------------------------------------

class TestGetForecast:
    """Tests for get_forecast()."""

    @patch("open_meteo_connector.requests.get")
    def test_returns_jua_named_keys_only(self, mock_get):
        """Result dict must use Jua variable names, never Open-Meteo names."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2))
        result = get_forecast(0.0, 0.0, [])
        for key in result["data_vars"]:
            assert key in VARIABLE_MAP, (
                f"Key '{key}' is not a Jua variable name"
            )
        om_names = set(VARIABLE_MAP.values())
        for key in result["data_vars"]:
            assert key not in om_names, (
                f"Open-Meteo name '{key}' leaked into result"
            )

    @patch("open_meteo_connector.requests.get")
    def test_temperature_converted_to_kelvin(self, mock_get):
        """Open-Meteo returns °C; result must store value in K."""
        temp_c = 0.0  # 0°C = 273.15 K
        mock_get.return_value = make_mock_response(make_om_response(0, temp_c, 0))
        result = get_forecast(0.0, 0.0, [])
        stored = result["data_vars"]["air_temperature_at_height_level_2m"]["data"]
        assert abs(stored - 273.15) < 0.001, (
            f"Expected 273.15 K, got {stored}"
        )

    @patch("open_meteo_connector.requests.get")
    def test_temperature_takes_minimum_kelvin(self, mock_get):
        """For temperature the worst-case (minimum) value is stored."""
        # Two values: 10°C and -5°C; min in K should be -5 + 273.15 = 268.15
        mock_get.return_value = make_mock_response({
            "hourly": {
                "windspeed_10m": [0, 0],
                "temperature_2m": [10.0, -5.0],
                "precipitation": [0, 0],
            }
        })
        result = get_forecast(0.0, 0.0, [], hours=2)
        stored = result["data_vars"]["air_temperature_at_height_level_2m"]["data"]
        assert abs(stored - 268.15) < 0.001, f"Expected 268.15 K, got {stored}"

    @patch("open_meteo_connector.requests.get")
    def test_wind_takes_maximum(self, mock_get):
        """For wind speed the peak (maximum) value is stored."""
        mock_get.return_value = make_mock_response({
            "hourly": {
                "windspeed_10m": [30.0, 95.0, 50.0],
                "temperature_2m": [15.0, 15.0, 15.0],
                "precipitation": [0, 0, 0],
            }
        })
        result = get_forecast(0.0, 0.0, [], hours=3)
        stored = result["data_vars"]["wind_speed_at_height_level_10m"]["data"]
        assert stored == 95.0, f"Expected 95.0, got {stored}"

    @patch("open_meteo_connector.requests.get")
    def test_default_variables_always_present_in_api_call(self, mock_get):
        """Even when variables=[], the three DEFAULT_VARIABLES are sent to the API."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2))
        get_forecast(1.0, 2.0, [])
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        hourly_param = params.get("hourly", "")
        for jua_var in DEFAULT_VARIABLES:
            om_var = VARIABLE_MAP[jua_var]
            assert om_var in hourly_param, (
                f"Default variable '{om_var}' missing from hourly param: {hourly_param}"
            )

    @patch("open_meteo_connector.requests.get")
    def test_no_duplicate_variables_when_defaults_passed_explicitly(self, mock_get):
        """Passing a DEFAULT_VARIABLE explicitly should not cause it to appear twice."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2))
        get_forecast(1.0, 2.0, [DEFAULT_VARIABLES[0]])
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        hourly_list = params.get("hourly", "").split(",")
        assert len(hourly_list) == len(set(hourly_list)), (
            f"Duplicate variables in API call: {hourly_list}"
        )

    @patch("open_meteo_connector.requests.get")
    def test_hours_1_requests_1_forecast_day(self, mock_get):
        """hours=1 → ceil(1/24)=1 forecast_days."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2, hours=24))
        get_forecast(0.0, 0.0, [], hours=1)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["forecast_days"] == 1

    @patch("open_meteo_connector.requests.get")
    def test_hours_1_slices_to_1_value(self, mock_get):
        """hours=1 → only the first hourly value is used."""
        mock_get.return_value = make_mock_response({
            "hourly": {
                "windspeed_10m": [10.0] + [999.0] * 23,
                "temperature_2m": [20.0] * 24,
                "precipitation": [0.0] * 24,
            }
        })
        result = get_forecast(0.0, 0.0, [], hours=1)
        # Only the first hour's wind (10.0) should be used — not 999.0
        stored_wind = result["data_vars"]["wind_speed_at_height_level_10m"]["data"]
        assert stored_wind == 10.0, f"Expected 10.0, got {stored_wind}"

    @patch("open_meteo_connector.requests.get")
    def test_hours_384_no_clamp(self, mock_get):
        """hours=384 = 16 days exactly; forecast_days should be 16, not clamped."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2, hours=384))
        get_forecast(0.0, 0.0, [], hours=384)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["forecast_days"] == 16

    @patch("open_meteo_connector.requests.get")
    def test_hours_385_clamped_to_16_days(self, mock_get):
        """hours=385 → ceil(385/24)=17 but must be clamped to 16."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2, hours=384))
        get_forecast(0.0, 0.0, [], hours=385)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["forecast_days"] == 16

    @patch("open_meteo_connector.requests.get")
    def test_network_exception_raises_runtime_error(self, mock_get):
        """A requests.RequestException must become a RuntimeError with 'network error'."""
        import requests as req_lib
        mock_get.side_effect = req_lib.ConnectionError("connection refused")
        with pytest.raises(RuntimeError) as exc_info:
            get_forecast(0.0, 0.0, [])
        assert "network error" in str(exc_info.value).lower()

    @patch("open_meteo_connector.requests.get")
    def test_http_error_response_raises_runtime_error(self, mock_get):
        """A non-2xx response must raise RuntimeError via _handle_http_error."""
        mock_get.return_value = make_mock_response({}, status_code=500)
        with pytest.raises(RuntimeError) as exc_info:
            get_forecast(0.0, 0.0, [])
        assert "500" in str(exc_info.value)

    @patch("open_meteo_connector.requests.get")
    def test_none_values_filtered_out(self, mock_get):
        """None values in the hourly array must be ignored."""
        mock_get.return_value = make_mock_response({
            "hourly": {
                "windspeed_10m": [None, None, 55.0],
                "temperature_2m": [None, 10.0, None],
                "precipitation": [None, None, None],
            }
        })
        result = get_forecast(0.0, 0.0, [])
        # Wind should survive (55.0 is present)
        assert "wind_speed_at_height_level_10m" in result["data_vars"]
        assert result["data_vars"]["wind_speed_at_height_level_10m"]["data"] == 55.0
        # Temp should survive (10.0 is present)
        assert "air_temperature_at_height_level_2m" in result["data_vars"]
        # Precip should be absent (all None)
        assert "precipitation_amount_at_surface" not in result["data_vars"]

    @patch("open_meteo_connector.requests.get")
    def test_wind_speed_unit_kmh_sent(self, mock_get):
        """wind_speed_unit=kmh must always be passed to the API."""
        mock_get.return_value = make_mock_response(make_om_response(50, 20, 2))
        get_forecast(1.0, 2.0, [])
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["wind_speed_unit"] == "kmh"


# ---------------------------------------------------------------------------
# TestGetRegionalForecast
# ---------------------------------------------------------------------------

class TestGetRegionalForecast:
    """Tests for get_regional_forecast()."""

    @patch("open_meteo_connector.get_forecast")
    def test_5_element_bbox_raises_value_error(self, mock_gf):
        with pytest.raises(ValueError):
            get_regional_forecast((0, 0, 1, 1, 2), [])

    @patch("open_meteo_connector.get_forecast")
    def test_3_element_bbox_raises_value_error(self, mock_gf):
        with pytest.raises(ValueError):
            get_regional_forecast((0, 0, 1), [])

    @patch("open_meteo_connector.get_forecast")
    def test_calls_get_forecast_four_times(self, mock_gf):
        """Four corners of the bbox must each trigger a get_forecast call."""
        mock_gf.return_value = {
            "data_vars": {
                "wind_speed_at_height_level_10m": {"data": 50.0},
                "air_temperature_at_height_level_2m": {"data": 280.0},
                "precipitation_amount_at_surface": {"data": 5.0},
            }
        }
        get_regional_forecast((10.0, 20.0, 11.0, 21.0), [])
        assert mock_gf.call_count == 4

    @patch("open_meteo_connector.get_forecast")
    def test_averages_values_across_corners(self, mock_gf):
        """Variable values must be averaged across all 4 corners."""
        mock_gf.side_effect = [
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 40.0},
                            "air_temperature_at_height_level_2m": {"data": 280.0},
                            "precipitation_amount_at_surface": {"data": 2.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 60.0},
                            "air_temperature_at_height_level_2m": {"data": 290.0},
                            "precipitation_amount_at_surface": {"data": 4.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 80.0},
                            "air_temperature_at_height_level_2m": {"data": 270.0},
                            "precipitation_amount_at_surface": {"data": 6.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 100.0},
                            "air_temperature_at_height_level_2m": {"data": 260.0},
                            "precipitation_amount_at_surface": {"data": 8.0}}},
        ]
        result = get_regional_forecast((0.0, 0.0, 1.0, 1.0), [])
        assert abs(result["data_vars"]["wind_speed_at_height_level_10m"]["data"] - 70.0) < 0.001
        assert abs(result["data_vars"]["precipitation_amount_at_surface"]["data"] - 5.0) < 0.001

    @patch("open_meteo_connector.get_forecast")
    def test_partial_data_skips_variable(self, mock_gf):
        """If one corner is missing a variable, that variable is excluded from the result."""
        # Corner 1 missing precipitation
        mock_gf.side_effect = [
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 50.0},
                            "air_temperature_at_height_level_2m": {"data": 280.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 50.0},
                            "air_temperature_at_height_level_2m": {"data": 280.0},
                            "precipitation_amount_at_surface": {"data": 5.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 50.0},
                            "air_temperature_at_height_level_2m": {"data": 280.0},
                            "precipitation_amount_at_surface": {"data": 5.0}}},
            {"data_vars": {"wind_speed_at_height_level_10m": {"data": 50.0},
                            "air_temperature_at_height_level_2m": {"data": 280.0},
                            "precipitation_amount_at_surface": {"data": 5.0}}},
        ]
        result = get_regional_forecast((0.0, 0.0, 1.0, 1.0), [])
        # precipitation should be absent because corner 1 lacks it
        assert "precipitation_amount_at_surface" not in result["data_vars"]
        # wind and temp should be present (all 4 corners have them)
        assert "wind_speed_at_height_level_10m" in result["data_vars"]
        assert "air_temperature_at_height_level_2m" in result["data_vars"]

    @patch("open_meteo_connector.get_forecast")
    def test_returns_data_vars_structure(self, mock_gf):
        """Return shape must be {'data_vars': {<var>: {'data': <float>}}}."""
        mock_gf.return_value = {
            "data_vars": {
                "wind_speed_at_height_level_10m": {"data": 50.0},
                "air_temperature_at_height_level_2m": {"data": 280.0},
                "precipitation_amount_at_surface": {"data": 5.0},
            }
        }
        result = get_regional_forecast((0.0, 0.0, 1.0, 1.0), [])
        assert "data_vars" in result
        for var, payload in result["data_vars"].items():
            assert "data" in payload, f"'data' key missing from var '{var}'"
            assert isinstance(payload["data"], float), (
                f"Expected float for '{var}', got {type(payload['data'])}"
            )


# ---------------------------------------------------------------------------
# TestScanRoute
# ---------------------------------------------------------------------------

class TestScanRoute:
    """Tests for scan_route()."""

    def _good_forecast(self, wind=50.0, temp_k=285.0, precip=3.0) -> dict:
        return {
            "data_vars": {
                "wind_speed_at_height_level_10m": {"data": wind},
                "air_temperature_at_height_level_2m": {"data": temp_k},
                "precipitation_amount_at_surface": {"data": precip},
            }
        }

    def _waypoints(self, n: int) -> list:
        return [(float(i), float(i)) for i in range(n)]

    def test_4_waypoints_raises_value_error_mentioning_5(self):
        with pytest.raises(ValueError, match="5"):
            scan_route(self._waypoints(4), [])

    def test_11_waypoints_raises_value_error_mentioning_10(self):
        with pytest.raises(ValueError, match="10"):
            scan_route(self._waypoints(11), [])

    @patch("open_meteo_connector.get_forecast")
    def test_5_waypoints_valid(self, mock_gf):
        mock_gf.return_value = self._good_forecast()
        result = scan_route(self._waypoints(5), [])
        assert len(result) == 5

    @patch("open_meteo_connector.get_forecast")
    def test_10_waypoints_valid(self, mock_gf):
        mock_gf.return_value = self._good_forecast()
        result = scan_route(self._waypoints(10), [])
        assert len(result) == 10

    @patch("open_meteo_connector.get_forecast")
    def test_output_preserves_input_order(self, mock_gf):
        """Results must appear in the same order as the input waypoints."""
        waypoints = [(float(i), float(i) * 2) for i in range(5)]
        mock_gf.return_value = self._good_forecast()
        result = scan_route(waypoints, [])
        for i, (lat, lon) in enumerate(waypoints):
            assert result[i]["lat"] == lat
            assert result[i]["lon"] == lon

    @patch("open_meteo_connector.get_forecast")
    def test_failed_middle_point_preserved_in_order(self, mock_gf):
        """A failing middle point must remain in position and not disturb neighbors."""
        waypoints = [(float(i), 0.0) for i in range(5)]
        # Points 0, 1, 3, 4 succeed; point 2 fails
        def side_effect(lat, lon, *args, **kwargs):
            if lat == 2.0:
                raise RuntimeError("simulated failure")
            return self._good_forecast()
        mock_gf.side_effect = side_effect
        result = scan_route(waypoints, [])
        assert len(result) == 5
        # Position 2 is the failed point
        assert result[2]["lat"] == 2.0
        assert result[2]["flagged"] is False
        assert result[2]["severity"] == "unknown"
        assert len(result[2]["error"]) > 0
        # Neighbors should be normal
        assert result[1]["flagged"] is not None
        assert "error" not in result[1]
        assert result[3]["flagged"] is not None
        assert "error" not in result[3]

    @patch("open_meteo_connector.get_forecast")
    def test_failed_point_structure(self, mock_gf):
        """Failed waypoint entry must have flagged=False, severity='unknown', non-empty error."""
        mock_gf.side_effect = RuntimeError("some error")
        result = scan_route(self._waypoints(5), [])
        for entry in result:
            assert entry["flagged"] is False
            assert entry["severity"] == "unknown"
            assert isinstance(entry.get("error"), str) and len(entry["error"]) > 0

    @patch("open_meteo_connector.get_forecast")
    def test_successful_point_has_no_error_key(self, mock_gf):
        """Successful waypoints must not have an 'error' key."""
        mock_gf.return_value = self._good_forecast()
        result = scan_route(self._waypoints(5), [])
        for entry in result:
            assert "error" not in entry

    @patch("open_meteo_connector.get_forecast")
    def test_returns_correct_lat_lon(self, mock_gf):
        """Each result entry must echo back the correct lat/lon."""
        mock_gf.return_value = self._good_forecast()
        waypoints = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0), (70.0, 80.0), (90.0, 100.0)]
        result = scan_route(waypoints, [])
        for i, (lat, lon) in enumerate(waypoints):
            assert result[i]["lat"] == lat
            assert result[i]["lon"] == lon


# ---------------------------------------------------------------------------
# TestClassifySeverity
# ---------------------------------------------------------------------------

class TestClassifySeverity:
    """Tests for _classify_severity() covering all documented thresholds."""

    # ----- parametrized boundary table -----

    @pytest.mark.parametrize("wind,precip,temp_k,expected_flagged,expected_severity", [
        # Wind thresholds
        # wind=90 is NOT severe (not > 90), but IS > 60, so it's minor (flagged=True)
        (90.0,  0.0, 290.0, True,  "minor"),    # wind == 90: not severe, but > 60 → minor
        (90.1,  0.0, 290.0, True,  "severe"),   # wind just above 90 → severe
        (60.0,  0.0, 290.0, False, "ok"),       # wind == 60 (not > 60, no flag)
        (60.1,  0.0, 290.0, True,  "minor"),    # wind just above 60 → minor
        # Precip threshold
        (0.0,  10.0, 290.0, False, "ok"),       # precip == 10 (not > 10, no flag)
        (0.0,  10.1, 290.0, True,  "minor"),    # precip just above 10 → minor
        # Temp threshold
        (0.0,   0.0, 268.0, False, "ok"),       # temp == 268 (not < 268, no flag)
        (0.0,   0.0, 267.9, True,  "minor"),    # temp just below 268 → minor
        # Two minors → moderate
        (61.0, 11.0, 290.0, True,  "moderate"), # wind minor + precip minor
        (61.0,  0.0, 267.0, True,  "moderate"), # wind minor + temp minor
        (0.0,  11.0, 267.0, True,  "moderate"), # precip minor + temp minor
        # Severe overrides moderate combination
        (91.0, 11.0, 267.0, True,  "severe"),   # severe wind overrides two minors
        # All clear
        (0.0,   0.0, 290.0, False, "ok"),       # nothing triggered
    ])
    def test_severity_boundaries(
        self, wind, precip, temp_k, expected_flagged, expected_severity
    ):
        conditions = {
            "wind_speed_at_height_level_10m": wind,
            "precipitation_amount_at_surface": precip,
            "air_temperature_at_height_level_2m": temp_k,
        }
        flagged, severity = _classify_severity(conditions)
        assert flagged == expected_flagged, (
            f"wind={wind} precip={precip} temp_k={temp_k}: "
            f"expected flagged={expected_flagged}, got {flagged}"
        )
        assert severity == expected_severity, (
            f"wind={wind} precip={precip} temp_k={temp_k}: "
            f"expected severity='{expected_severity}', got '{severity}'"
        )

    def test_missing_keys_treated_as_none(self):
        """Missing keys in conditions dict must not raise errors."""
        flagged, severity = _classify_severity({})
        assert flagged is False
        assert severity == "ok"

    def test_only_wind_present_severe(self):
        flagged, severity = _classify_severity(
            {"wind_speed_at_height_level_10m": 100.0}
        )
        assert flagged is True
        assert severity == "severe"

    def test_only_precip_present_minor(self):
        flagged, severity = _classify_severity(
            {"precipitation_amount_at_surface": 15.0}
        )
        assert flagged is True
        assert severity == "minor"

    def test_only_temp_present_minor(self):
        flagged, severity = _classify_severity(
            {"air_temperature_at_height_level_2m": 260.0}
        )
        assert flagged is True
        assert severity == "minor"

    def test_three_minors_is_moderate(self):
        """Three minor triggers still only reach 'moderate' (severe requires wind>90)."""
        conditions = {
            "wind_speed_at_height_level_10m": 61.0,   # minor
            "precipitation_amount_at_surface": 11.0,  # minor
            "air_temperature_at_height_level_2m": 267.0,  # minor
        }
        flagged, severity = _classify_severity(conditions)
        assert flagged is True
        assert severity == "moderate"
