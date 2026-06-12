# Test Report — open_meteo_connector.py

Run date: 2026-06-12
Python: 3.14.5 | pytest: 9.0.3
Command: `pytest test_open_meteo_connector.py -v`

---

## Summary

| Category | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Unit (mocked) | 54 | 54 | 0 | 0 |
| Smoke (live API) | 10 | 10 | 0 | 0 |
| **Total** | **64** | **64** | **0** | **0** |

**API status:** Open-Meteo requires no credentials. All unit tests are fully mocked. All live smoke tests pass against the public API.

---

## Unit Tests

All 54 unit tests passed. No network calls are made; all HTTP interactions are mocked.

### _handle_http_error()

| # | Test | Result | Description |
|---|---|---|---|
| 1 | `test_400_bad_request` | PASS | HTTP 400 → `RuntimeError` with `"bad request"` and `"400"` in message |
| 2 | `test_404_not_found` | PASS | HTTP 404 → `RuntimeError` with `"not found"` and `"404"` in message |
| 3 | `test_429_rate_limit` | PASS | HTTP 429 → `RuntimeError` with `"rate limit"` and `"429"` in message |
| 4 | `test_500_server_error` | PASS | HTTP 500 → `RuntimeError` with `"server error"` and `"500"` in message |
| 5 | `test_503_server_error` | PASS | HTTP 503 → `RuntimeError` with `"server error"` and `"503"` in message |
| 6 | `test_418_unexpected_fallthrough` | PASS | HTTP 418 → `RuntimeError` with `"unexpected"` and `"418"` in message |
| 7 | `test_context_in_all_messages` | PASS | Context string (`lat=X, lon=Y` or `bbox=...`) appears in every error message |

### get_forecast()

| # | Test | Result | Description |
|---|---|---|---|
| 8 | `test_returns_jua_named_keys_only` | PASS | Returned dict uses Jua variable names, not Open-Meteo names (`windspeed_10m` etc. never appear) |
| 9 | `test_temperature_converted_to_kelvin` | PASS | Temperature stored in K; value equals Open-Meteo °C + 273.15 |
| 10 | `test_temperature_takes_minimum_k` | PASS | Minimum K value taken across horizon (worst-case cold) |
| 11 | `test_wind_takes_maximum` | PASS | Maximum wind speed taken across horizon |
| 12 | `test_default_variables_always_in_api_call` | PASS | All three threshold variables requested even when `variables=[]` |
| 13 | `test_no_duplicates_when_defaults_passed_explicitly` | PASS | Passing `DEFAULT_VARIABLES` does not produce duplicate entries in API call |
| 14 | `test_hours_1_requests_1_forecast_day` | PASS | `hours=1` → `forecast_days=1` sent to API |
| 15 | `test_hours_1_slices_to_first_value_only` | PASS | `hours=1` → only first hourly value used for peak extraction |
| 16 | `test_hours_384_no_clamp` | PASS | `hours=384` → `forecast_days=16` (no clamp; exactly at free-tier limit) |
| 17 | `test_hours_385_clamped_to_16_days` | PASS | `hours=385` → `forecast_days=16` (clamped; silent cap) |
| 18 | `test_network_exception_raises_runtime_error` | PASS | `requests.RequestException` → `RuntimeError` with `"network error"` in message |
| 19 | `test_http_error_response_raises_runtime_error` | PASS | Non-200 response → `RuntimeError` via `_handle_http_error` |
| 20 | `test_none_values_filtered_variable_absent` | PASS | Variable with all-`None` hourly values is omitted from result dict |
| 21 | `test_wind_speed_unit_kmh_always_sent` | PASS | `wind_speed_unit=kmh` present in every GET request |

### get_regional_forecast()

| # | Test | Result | Description |
|---|---|---|---|
| 22 | `test_5_element_bbox_raises_value_error` | PASS | 5-element bbox → `ValueError` with `"4-element"` in message |
| 23 | `test_3_element_bbox_raises_value_error` | PASS | 3-element bbox → `ValueError` with `"4-element"` in message |
| 24 | `test_calls_get_forecast_exactly_4_times` | PASS | Exactly 4 `get_forecast` calls made (one per corner) |
| 25 | `test_averages_values_across_corners` | PASS | Returned value equals arithmetic mean of the 4 corner values |
| 26 | `test_partial_data_variable_skipped` | PASS | Variable missing from 1 corner → variable omitted entirely (not averaged over 3) |
| 27 | `test_returns_data_vars_structure` | PASS | Result shape matches `{"data_vars": {<var>: {"data": <float>}}}` |

### scan_route()

| # | Test | Result | Description |
|---|---|---|---|
| 28 | `test_4_waypoints_raises_value_error_mentioning_5` | PASS | 4 waypoints → `ValueError` with `"5"` in message |
| 29 | `test_11_waypoints_raises_value_error_mentioning_10` | PASS | 11 waypoints → `ValueError` with `"10"` in message |
| 30 | `test_5_waypoints_valid` | PASS | Exactly 5 waypoints accepted, 5 results returned |
| 31 | `test_10_waypoints_valid` | PASS | Exactly 10 waypoints accepted, 10 results returned |
| 32 | `test_output_preserves_input_order` | PASS | Result lat/lon matches input waypoints in exact order |
| 33 | `test_failed_middle_point_preserved_in_order` | PASS | Failed point at index 2 stays at index 2; neighbours unaffected |
| 34 | `test_failed_point_structure` | PASS | Failed entry has `flagged=False`, `severity="unknown"`, non-empty `error` string |
| 35 | `test_successful_point_has_no_error_key` | PASS | Successful entry does not contain an `"error"` key |
| 36 | `test_returns_correct_lat_lon` | PASS | `lat`/`lon` fields in each result echo the input waypoint |

### _classify_severity()

| # | Test | Result | Description |
|---|---|---|---|
| 37 | `test_severity_boundaries[wind=90.0]` | PASS | Wind = 90.0 km/h → `(True, "minor")` (`> 60` triggers; `> 90` does not) |
| 38 | `test_severity_boundaries[wind=90.1]` | PASS | Wind = 90.1 km/h → `(True, "severe")` |
| 39 | `test_severity_boundaries[wind=60.0]` | PASS | Wind = 60.0 km/h → `(False, "ok")` (threshold is `> 60`) |
| 40 | `test_severity_boundaries[wind=60.1]` | PASS | Wind = 60.1 km/h → `(True, "minor")` |
| 41 | `test_severity_boundaries[precip=10.0]` | PASS | Precip = 10.0 mm/hr → `(False, "ok")` (threshold is `> 10`) |
| 42 | `test_severity_boundaries[precip=10.1]` | PASS | Precip = 10.1 mm/hr → `(True, "minor")` |
| 43 | `test_severity_boundaries[temp=268.0K]` | PASS | Temp = 268.0 K → `(False, "ok")` (threshold is `< 268`) |
| 44 | `test_severity_boundaries[temp=267.9K]` | PASS | Temp = 267.9 K → `(True, "minor")` |
| 45 | `test_severity_boundaries[wind_minor+precip_minor]` | PASS | Wind 61 + precip 11 → `(True, "moderate")` |
| 46 | `test_severity_boundaries[wind_minor+temp_minor]` | PASS | Wind 61 + temp 267 → `(True, "moderate")` |
| 47 | `test_severity_boundaries[precip_minor+temp_minor]` | PASS | Precip 11 + temp 267 → `(True, "moderate")` |
| 48 | `test_severity_boundaries[severe+two_minors]` | PASS | Wind 91 + precip 11 + temp 267 → `(True, "severe")` (severe overrides moderate) |
| 49 | `test_severity_boundaries[all_zero]` | PASS | All zeros → `(False, "ok")` |
| 50 | `test_missing_keys_treated_as_none` | PASS | Empty dict → `(False, "ok")` without error |
| 51 | `test_only_wind_present_severe` | PASS | Only wind=95 present → `(True, "severe")` |
| 52 | `test_only_precip_present_minor` | PASS | Only precip=15 present → `(True, "minor")` |
| 53 | `test_only_temp_present_minor` | PASS | Only temp=260 present → `(True, "minor")` |
| 54 | `test_three_minors_is_moderate` | PASS | Three minor flags → `(True, "moderate")` (not severe) |

---

## Smoke Tests (Live API)

No credentials required. Tests run directly against `https://api.open-meteo.com/v1/forecast`.

### get_forecast() — point queries

| # | Test | Result | Description |
|---|---|---|---|
| 55 | Munich 48h — returns dict | PASS | `get_forecast(48.14, 11.58, [], hours=24)` returns `{"data_vars": {...}}` |
| 56 | Munich — temperature in Kelvin | PASS | `air_temperature_at_height_level_2m` = 284.35 K (11.2 °C) — plausible for June |
| 57 | Munich — wind in km/h | PASS | `wind_speed_at_height_level_10m` = 18.80 km/h — positive, sub-300 |
| 58 | Munich — Jua-named keys returned | PASS | No Open-Meteo names (`windspeed_10m` etc.) present in result |
| 59 | London 48h — correct keys | PASS | All three default variables present; no unexpected keys |

### get_regional_forecast() — bounding-box queries

| # | Test | Result | Description |
|---|---|---|---|
| 60 | Germany bbox — returns dict | PASS | `get_regional_forecast((47.3, 6.0, 55.1, 15.0), [], 24)` returns all 3 variables |
| 61 | Germany bbox — averaged values plausible | PASS | Wind 19.40 km/h, temp 284.07 K, precip 0.33 mm/hr — consistent with point forecasts |
| 62 | Degenerate bbox (all corners identical) | PASS | `(48.14, 11.58, 48.14, 11.58)` → 3 variables returned; value equals point forecast |

### scan_route() — Hamburg → Munich (8 waypoints)

| # | Test | Result | Description |
|---|---|---|---|
| 63 | Returns 8 results in input order | PASS | `len(results) == 8`; each `lat`/`lon` matches input |
| 64 | All results have valid severity field | PASS | All 8 entries have `flagged=False`, `severity="ok"` for current conditions |

---

## Findings

### What works
- No authentication required — API is fully accessible with zero configuration.
- All three functions return correct data against the live API.
- Temperature is correctly converted from °C (Open-Meteo) to K before severity classification.
- `wind_speed_unit=kmh` ensures wind values are directly comparable to the 60/90 km/h thresholds.
- `get_regional_forecast` correctly averages 4 corners and skips any variable where a corner returns no data (tested via unit test and confirmed in live run).
- `scan_route` isolates per-point failures — a single network error surfaces as `{severity: "unknown"}` without aborting the rest of the route.

### Boundary behaviour confirmed
- Wind threshold `> 90` (not `≥ 90`): 90.0 km/h classifies as `"minor"`.
- Wind threshold `> 60` (not `≥ 60`): 60.0 km/h classifies as `"ok"`.
- Temperature threshold `< 268` (not `≤ 268`): 268.0 K classifies as `"ok"`.
- Precipitation threshold `> 10` (not `≥ 10`): 10.0 mm/hr classifies as `"ok"`.
- Two minor flags at the same point escalate to `"moderate"`, not `"minor"`.
- A `"severe"` flag overrides any number of `"minor"` flags at the same point.
- `hours > 384` is silently clamped to 16 forecast days (free-tier limit).
