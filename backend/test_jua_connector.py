"""
Tests for jua_connector.py.

Structure:
  - Unit tests (fully mocked, no network): test logic and error handling in isolation.
  - Smoke tests (live network, real credentials): validate actual SDK integration.

Run all:      pytest test_jua_connector.py -v
Run units:    pytest test_jua_connector.py -v -m unit
Run smoke:    pytest test_jua_connector.py -v -m smoke
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REAL_CREDS = bool(os.environ.get("JUA_KEY_ID") and os.environ.get("JUA_SECRET"))

HAMBURG_MUNICH = [
    (53.55, 10.00),
    (53.20, 10.40),
    (52.80, 10.90),
    (52.40, 11.50),
    (52.10, 12.10),
    (51.60, 12.40),
    (51.00, 11.60),
    (48.14, 11.58),
]


def _make_xarray_dict(wind=50.0, temp=280.0, precip=2.0):
    """Return a minimal xarray .to_dict() structure with scalar values."""
    return {
        "data_vars": {
            "wind_speed_at_height_level_10m": {"data": wind},
            "air_temperature_at_height_level_2m": {"data": temp},
            "precipitation_amount_at_surface": {"data": precip},
        }
    }


# ---------------------------------------------------------------------------
# Unit tests — authenticate()
# ---------------------------------------------------------------------------


class TestAuthenticate:
    @pytest.mark.unit
    def test_raises_on_missing_key_id(self):
        with patch.dict(os.environ, {"JUA_KEY_ID": "", "JUA_SECRET": "secret"}):
            from jua_connector import authenticate
            with pytest.raises(ValueError, match="JUA_KEY_ID"):
                authenticate()

    @pytest.mark.unit
    def test_raises_on_missing_secret(self):
        with patch.dict(os.environ, {"JUA_KEY_ID": "keyid", "JUA_SECRET": ""}):
            from jua_connector import authenticate
            with pytest.raises(ValueError, match="JUA_SECRET"):
                authenticate()

    @pytest.mark.unit
    def test_raises_on_both_missing(self, monkeypatch):
        monkeypatch.delenv("JUA_KEY_ID", raising=False)
        monkeypatch.delenv("JUA_SECRET", raising=False)
        from jua_connector import authenticate
        with pytest.raises(ValueError):
            authenticate()

    @pytest.mark.unit
    def test_returns_client_when_creds_present(self):
        mock_client = MagicMock()
        with patch.dict(os.environ, {"JUA_KEY_ID": "kid", "JUA_SECRET": "sec"}):
            with patch("jua_connector.JuaClient", return_value=mock_client):
                from jua_connector import authenticate
                result = authenticate()
        assert result is mock_client


# ---------------------------------------------------------------------------
# Unit tests — _classify_severity()
# ---------------------------------------------------------------------------


class TestClassifySeverity:
    @pytest.mark.unit
    def test_no_flags_returns_ok(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 30.0,
            "air_temperature_at_height_level_2m": 285.0,
            "precipitation_amount_at_surface": 1.0,
        })
        assert flagged is False
        assert severity == "ok"

    @pytest.mark.unit
    def test_wind_above_60_is_minor(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 75.0,
            "air_temperature_at_height_level_2m": 285.0,
            "precipitation_amount_at_surface": 0.0,
        })
        assert flagged is True
        assert severity == "minor"

    @pytest.mark.unit
    def test_wind_above_90_is_severe(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 95.0,
            "air_temperature_at_height_level_2m": 285.0,
            "precipitation_amount_at_surface": 0.0,
        })
        assert flagged is True
        assert severity == "severe"

    @pytest.mark.unit
    def test_precip_above_10_is_minor(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 10.0,
            "air_temperature_at_height_level_2m": 285.0,
            "precipitation_amount_at_surface": 15.0,
        })
        assert flagged is True
        assert severity == "minor"

    @pytest.mark.unit
    def test_temp_below_268_is_minor(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 10.0,
            "air_temperature_at_height_level_2m": 260.0,
            "precipitation_amount_at_surface": 0.0,
        })
        assert flagged is True
        assert severity == "minor"

    @pytest.mark.unit
    def test_two_minor_flags_is_moderate(self):
        from jua_connector import _classify_severity
        # wind minor + precip minor → moderate
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 70.0,
            "air_temperature_at_height_level_2m": 285.0,
            "precipitation_amount_at_surface": 15.0,
        })
        assert flagged is True
        assert severity == "moderate"

    @pytest.mark.unit
    def test_three_minor_flags_is_moderate(self):
        from jua_connector import _classify_severity
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 70.0,
            "air_temperature_at_height_level_2m": 260.0,
            "precipitation_amount_at_surface": 15.0,
        })
        assert flagged is True
        assert severity == "moderate"

    @pytest.mark.unit
    def test_severe_overrides_minor_flags(self):
        from jua_connector import _classify_severity
        # wind severe + precip minor + temp minor → severe (not moderate)
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 100.0,
            "air_temperature_at_height_level_2m": 260.0,
            "precipitation_amount_at_surface": 15.0,
        })
        assert flagged is True
        assert severity == "severe"

    @pytest.mark.unit
    def test_missing_variables_skipped(self):
        from jua_connector import _classify_severity
        # Empty conditions — nothing to flag
        flagged, severity = _classify_severity({})
        assert flagged is False
        assert severity == "ok"

    @pytest.mark.unit
    def test_wind_exactly_at_90_is_minor_not_severe(self):
        from jua_connector import _classify_severity
        # Boundary: > 90 is severe, == 90 is minor
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 90.0,
        })
        assert severity == "minor"

    @pytest.mark.unit
    def test_wind_exactly_at_60_is_ok_not_minor(self):
        from jua_connector import _classify_severity
        # Boundary: > 60 is minor, == 60 is ok
        flagged, severity = _classify_severity({
            "wind_speed_at_height_level_10m": 60.0,
        })
        assert severity == "ok"


# ---------------------------------------------------------------------------
# Unit tests — scan_route() validation
# ---------------------------------------------------------------------------


class TestScanRouteValidation:
    @pytest.mark.unit
    def test_raises_on_fewer_than_5_waypoints(self):
        from jua_connector import scan_route
        with pytest.raises(ValueError, match="5"):
            scan_route([(0, 0)] * 4, variables=[])

    @pytest.mark.unit
    def test_raises_on_more_than_10_waypoints(self):
        from jua_connector import scan_route
        with pytest.raises(ValueError, match="10"):
            scan_route([(0, 0)] * 11, variables=[])

    @pytest.mark.unit
    def test_exactly_5_waypoints_accepted(self):
        from jua_connector import scan_route
        mock_data = _make_xarray_dict()
        with patch("jua_connector.get_forecast", return_value=mock_data):
            results = scan_route([(0, 0)] * 5, variables=[])
        assert len(results) == 5

    @pytest.mark.unit
    def test_exactly_10_waypoints_accepted(self):
        from jua_connector import scan_route
        mock_data = _make_xarray_dict()
        with patch("jua_connector.get_forecast", return_value=mock_data):
            results = scan_route([(0, 0)] * 10, variables=[])
        assert len(results) == 10


# ---------------------------------------------------------------------------
# Unit tests — scan_route() behaviour
# ---------------------------------------------------------------------------


class TestScanRouteBehaviour:
    @pytest.mark.unit
    def test_output_order_matches_input(self):
        from jua_connector import scan_route
        waypoints = [(float(i), float(i)) for i in range(5)]
        mock_data = _make_xarray_dict()
        with patch("jua_connector.get_forecast", return_value=mock_data):
            results = scan_route(waypoints, variables=[])
        for i, (lat, lon) in enumerate(waypoints):
            assert results[i]["lat"] == lat
            assert results[i]["lon"] == lon

    @pytest.mark.unit
    def test_failed_point_does_not_abort_scan(self):
        from jua_connector import scan_route
        good_data = _make_xarray_dict()
        call_count = 0

        def side_effect(lat, lon, variables, hours):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("simulated API failure")
            return good_data

        with patch("jua_connector.get_forecast", side_effect=side_effect):
            results = scan_route([(0, 0)] * 5, variables=[])

        assert len(results) == 5
        assert results[2]["severity"] == "unknown"
        assert results[2]["flagged"] is False
        assert "error" in results[2]

    @pytest.mark.unit
    def test_failed_point_error_field_is_non_empty(self):
        from jua_connector import scan_route
        good_data = _make_xarray_dict()

        def side_effect(lat, lon, variables, hours):
            if lat == 1.0:
                raise RuntimeError("network timeout")
            return good_data

        waypoints = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0)]
        with patch("jua_connector.get_forecast", side_effect=side_effect):
            results = scan_route(waypoints, variables=[])

        assert results[1]["error"] == "network timeout"

    @pytest.mark.unit
    def test_successful_point_has_required_keys(self):
        from jua_connector import scan_route
        with patch("jua_connector.get_forecast", return_value=_make_xarray_dict()):
            results = scan_route([(0, 0)] * 5, variables=[])
        for r in results:
            assert "lat" in r
            assert "lon" in r
            assert "flagged" in r
            assert "severity" in r


# ---------------------------------------------------------------------------
# Unit tests — get_regional_forecast() bbox validation
# ---------------------------------------------------------------------------


class TestGetRegionalForecast:
    @pytest.mark.unit
    def test_raises_on_3_element_bbox(self):
        from jua_connector import get_regional_forecast
        with pytest.raises(ValueError, match="4-element"):
            get_regional_forecast((1.0, 2.0, 3.0), variables=[])

    @pytest.mark.unit
    def test_raises_on_5_element_bbox(self):
        from jua_connector import get_regional_forecast
        with pytest.raises(ValueError, match="4-element"):
            get_regional_forecast((1.0, 2.0, 3.0, 4.0, 5.0), variables=[])

    @pytest.mark.unit
    def test_valid_bbox_calls_sdk(self):
        from jua_connector import get_regional_forecast
        mock_ds = MagicMock()
        mock_ds.to_xarray.return_value.to_dict.return_value = {"data_vars": {}}
        mock_model = MagicMock()
        mock_model.get_forecasts.return_value = mock_ds
        mock_client = MagicMock()
        mock_client.weather.get_model.return_value = mock_model

        with patch("jua_connector.authenticate", return_value=mock_client):
            result = get_regional_forecast((47.0, 6.0, 55.0, 15.0), variables=[])

        mock_model.get_forecasts.assert_called_once()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Unit tests — DEFAULT_VARIABLES always merged
# ---------------------------------------------------------------------------


class TestDefaultVariablesMerge:
    @pytest.mark.unit
    def test_default_variables_added_when_absent(self):
        from jua_connector import get_forecast, DEFAULT_VARIABLES
        mock_ds = MagicMock()
        mock_ds.to_xarray.return_value.to_dict.return_value = {"data_vars": {}}
        mock_model = MagicMock()
        mock_model.get_forecasts.return_value = mock_ds
        mock_client = MagicMock()
        mock_client.weather.get_model.return_value = mock_model

        with patch("jua_connector.authenticate", return_value=mock_client):
            get_forecast(0.0, 0.0, variables=[])

        call_kwargs = mock_model.get_forecasts.call_args.kwargs
        requested = call_kwargs["variables"]
        for v in DEFAULT_VARIABLES:
            assert v in requested

    @pytest.mark.unit
    def test_no_duplicate_variables(self):
        from jua_connector import get_forecast, DEFAULT_VARIABLES
        mock_ds = MagicMock()
        mock_ds.to_xarray.return_value.to_dict.return_value = {"data_vars": {}}
        mock_model = MagicMock()
        mock_model.get_forecasts.return_value = mock_ds
        mock_client = MagicMock()
        mock_client.weather.get_model.return_value = mock_model

        with patch("jua_connector.authenticate", return_value=mock_client):
            get_forecast(0.0, 0.0, variables=DEFAULT_VARIABLES)

        call_kwargs = mock_model.get_forecasts.call_args.kwargs
        requested = call_kwargs["variables"]
        assert len(requested) == len(set(requested))


# ---------------------------------------------------------------------------
# Smoke tests — live network, real credentials
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.skipif(not REAL_CREDS, reason="No real Jua credentials in environment")
class TestSmokeAuthenticate:
    def test_authenticate_returns_client(self):
        from jua_connector import authenticate
        client = authenticate()
        assert client is not None


@pytest.mark.smoke
@pytest.mark.skipif(not REAL_CREDS, reason="No real Jua credentials in environment")
class TestSmokeGetForecast:
    def test_point_forecast_munich_returns_dict(self):
        from jua_connector import get_forecast
        data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
        assert isinstance(data, dict)
        assert "data_vars" in data

    def test_point_forecast_contains_wind_variable(self):
        from jua_connector import get_forecast
        data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
        assert "wind_speed_at_height_level_10m" in data["data_vars"]

    def test_point_forecast_contains_temperature_variable(self):
        from jua_connector import get_forecast
        data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
        assert "air_temperature_at_height_level_2m" in data["data_vars"]

    def test_point_forecast_contains_precipitation_variable(self):
        from jua_connector import get_forecast
        data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
        assert "precipitation_amount_at_surface" in data["data_vars"]


@pytest.mark.smoke
@pytest.mark.skipif(not REAL_CREDS, reason="No real Jua credentials in environment")
class TestSmokeGetRegionalForecast:
    def test_regional_forecast_germany_returns_dict(self):
        from jua_connector import get_regional_forecast
        data = get_regional_forecast(
            bbox=(47.3, 6.0, 55.1, 15.0), variables=[], hours=24
        )
        assert isinstance(data, dict)
        assert "data_vars" in data


@pytest.mark.smoke
@pytest.mark.skipif(not REAL_CREDS, reason="No real Jua credentials in environment")
class TestSmokeScanRoute:
    def test_hamburg_munich_returns_8_results(self):
        from jua_connector import scan_route
        results = scan_route(HAMBURG_MUNICH, variables=[], hours=24)
        assert len(results) == 8

    def test_results_preserve_waypoint_order(self):
        from jua_connector import scan_route
        results = scan_route(HAMBURG_MUNICH, variables=[], hours=24)
        for i, (lat, lon) in enumerate(HAMBURG_MUNICH):
            assert results[i]["lat"] == lat
            assert results[i]["lon"] == lon

    def test_all_results_have_severity_field(self):
        from jua_connector import scan_route
        results = scan_route(HAMBURG_MUNICH, variables=[], hours=24)
        for r in results:
            assert "severity" in r
            assert r["severity"] in {"ok", "minor", "moderate", "severe", "unknown"}

    def test_no_results_missing_flagged_field(self):
        from jua_connector import scan_route
        results = scan_route(HAMBURG_MUNICH, variables=[], hours=24)
        for r in results:
            assert "flagged" in r
            assert isinstance(r["flagged"], bool)

    def test_bad_credentials_raises_runtime_error(self):
        with patch.dict(os.environ, {"JUA_KEY_ID": "bad", "JUA_SECRET": "creds"}):
            from jua_connector import get_forecast
            with pytest.raises(RuntimeError, match="401|authentication|credentials"):
                get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
