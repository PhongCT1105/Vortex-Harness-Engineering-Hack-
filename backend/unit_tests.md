# Test Report — jua_connector.py

Run date: 2026-06-12
Python: 3.14.5 | pytest: 9.0.3
Command: `pytest test_jua_connector.py -v`

---

## Summary

| Category | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Unit (mocked) | 28 | 28 | 0 | 0 |
| Smoke (live API) | 11 | 6 | 5 | 0 |
| **Total** | **39** | **34** | **5** | **0** |

**Credential status:** `JUA_KEY_ID` / `JUA_SECRET` present and valid for authentication. Account tier does not include grid/query-engine access (EPT2 point and regional queries return HTTP 403). `scan_route` passes by design — per-point failures are isolated.

---

## Unit Tests

All 28 unit tests passed. No network calls are made; all SDK interactions are mocked.

### authenticate()

| # | Test | Result | Description |
|---|---|---|---|
| 1 | `test_raises_on_missing_key_id` | PASS | `ValueError` raised with `"JUA_KEY_ID"` in message when env var is empty |
| 2 | `test_raises_on_missing_secret` | PASS | `ValueError` raised with `"JUA_SECRET"` in message when env var is empty |
| 3 | `test_raises_on_both_missing` | PASS | `ValueError` raised when both vars are absent from environment |
| 4 | `test_returns_client_when_creds_present` | PASS | Returns mocked `JuaClient` instance when both vars are set |

### _classify_severity()

| # | Test | Result | Description |
|---|---|---|---|
| 5 | `test_no_flags_returns_ok` | PASS | All values within thresholds → `(False, "ok")` |
| 6 | `test_wind_above_60_is_minor` | PASS | Wind = 75 km/h → `(True, "minor")` |
| 7 | `test_wind_above_90_is_severe` | PASS | Wind = 95 km/h → `(True, "severe")` |
| 8 | `test_precip_above_10_is_minor` | PASS | Precip = 15 mm/hr → `(True, "minor")` |
| 9 | `test_temp_below_268_is_minor` | PASS | Temp = 260 K → `(True, "minor")` |
| 10 | `test_two_minor_flags_is_moderate` | PASS | Wind 70 + precip 15 → `(True, "moderate")` |
| 11 | `test_three_minor_flags_is_moderate` | PASS | Wind 70 + temp 260 + precip 15 → `(True, "moderate")` |
| 12 | `test_severe_overrides_minor_flags` | PASS | Wind 100 + temp 260 + precip 15 → `(True, "severe")` not `"moderate"` |
| 13 | `test_missing_variables_skipped` | PASS | Empty conditions dict → `(False, "ok")` without error |
| 14 | `test_wind_exactly_at_90_is_minor_not_severe` | PASS | Wind = 90.0 km/h → `"minor"` (threshold is `> 90`, not `>= 90`) |
| 15 | `test_wind_exactly_at_60_is_ok_not_minor` | PASS | Wind = 60.0 km/h → `"ok"` (threshold is `> 60`, not `>= 60`) |

### scan_route() — input validation

| # | Test | Result | Description |
|---|---|---|---|
| 16 | `test_raises_on_fewer_than_5_waypoints` | PASS | 4 waypoints → `ValueError` mentioning `5` |
| 17 | `test_raises_on_more_than_10_waypoints` | PASS | 11 waypoints → `ValueError` mentioning `10` |
| 18 | `test_exactly_5_waypoints_accepted` | PASS | 5 waypoints → no error, 5 results returned |
| 19 | `test_exactly_10_waypoints_accepted` | PASS | 10 waypoints → no error, 10 results returned |

### scan_route() — behaviour

| # | Test | Result | Description |
|---|---|---|---|
| 20 | `test_output_order_matches_input` | PASS | Result list lat/lon matches input waypoints in order |
| 21 | `test_failed_point_does_not_abort_scan` | PASS | Exception on waypoint 3 of 5 → remaining 4 still processed |
| 22 | `test_failed_point_error_field_is_non_empty` | PASS | Failed point carries original exception message in `"error"` field |
| 23 | `test_successful_point_has_required_keys` | PASS | Each result dict contains `lat`, `lon`, `flagged`, `severity` |

### get_regional_forecast() — bbox validation

| # | Test | Result | Description |
|---|---|---|---|
| 24 | `test_raises_on_3_element_bbox` | PASS | 3-element tuple → `ValueError` with `"4-element"` in message |
| 25 | `test_raises_on_5_element_bbox` | PASS | 5-element tuple → `ValueError` with `"4-element"` in message |
| 26 | `test_valid_bbox_calls_sdk` | PASS | 4-element bbox → SDK `get_forecasts` called once, dict returned |

### DEFAULT_VARIABLES merge behaviour

| # | Test | Result | Description |
|---|---|---|---|
| 27 | `test_default_variables_added_when_absent` | PASS | All three threshold variables present in SDK call even when `variables=[]` |
| 28 | `test_no_duplicate_variables` | PASS | Passing `DEFAULT_VARIABLES` explicitly does not produce duplicates in SDK call |

---

## Smoke Tests (Live API)

Credentials: `JUA_KEY_ID` and `JUA_SECRET` loaded from `.env`.

### authenticate()

| # | Test | Result | Description |
|---|---|---|---|
| 29 | `test_authenticate_returns_client` | PASS | `JuaClient` returned successfully with real credentials |

### get_forecast() — point query (Munich 48.14°N, 11.58°E)

| # | Test | Result | Error |
|---|---|---|---|
| 30 | `test_point_forecast_munich_returns_dict` | FAIL | `RuntimeError: Jua request forbidden (lat=48.14, lon=11.58): account lacks access to this resource (HTTP 403)` |
| 31 | `test_point_forecast_contains_wind_variable` | FAIL | Same as above |
| 32 | `test_point_forecast_contains_temperature_variable` | FAIL | Same as above |
| 33 | `test_point_forecast_contains_precipitation_variable` | FAIL | Same as above |

**Root cause:** The account's API key authenticates successfully (HTTP 200 on auth) but does not have grid/query-engine access for EPT2 point forecasts. The Jua API returns HTTP 403 from the query engine endpoint. This is a plan/tier restriction on the account, not a code defect — error handling works correctly and produces a readable message.

### get_regional_forecast() — Germany bbox

| # | Test | Result | Error |
|---|---|---|---|
| 34 | `test_regional_forecast_germany_returns_dict` | FAIL | `RuntimeError: Jua request forbidden (bbox=(47.3, 6.0, 55.1, 15.0)): account lacks access to this resource (HTTP 403)` |

**Root cause:** Same tier restriction as above. Regional queries also require grid access.

### scan_route() — Hamburg → Munich (8 waypoints)

| # | Test | Result | Description |
|---|---|---|---|
| 35 | `test_hamburg_munich_returns_8_results` | PASS | 8 results returned (all with `severity: "unknown"` due to per-point 403 failures — graceful isolation working correctly) |
| 36 | `test_results_preserve_waypoint_order` | PASS | lat/lon in results match input waypoints in order |
| 37 | `test_all_results_have_severity_field` | PASS | All 8 results have `severity` ∈ `{ok, minor, moderate, severe, unknown}` |
| 38 | `test_no_results_missing_flagged_field` | PASS | All 8 results have `flagged` as a boolean |

### scan_route() — error handling

| # | Test | Result | Description |
|---|---|---|---|
| 39 | `test_bad_credentials_raises_runtime_error` | PASS | Invalid `JUA_KEY_ID`/`JUA_SECRET` → `RuntimeError` with `401`/`authentication`/`credentials` in message |

---

## Findings

### What works
- Authentication and credential validation are fully functional.
- All local logic (severity classification, waypoint bounds, bbox validation, variable merging, error isolation, output ordering) is correct across 28 unit tests.
- `scan_route` correctly isolates per-point API failures — a 403 on each waypoint surfaces as `{severity: "unknown", flagged: False, error: "..."}` without aborting the scan.
- Error messages for HTTP 401/403 are readable and correctly identify the context (lat/lon or bbox).

### What requires account upgrade
The 5 smoke failures (tests 30–34) are not code bugs. They indicate the Jua account does not have query-engine / grid access for EPT2. To make these tests pass, the account needs to be upgraded to a tier that grants access to `https://query.jua.ai/v1/forecast/`. No code changes are needed.

### Boundary behaviour confirmed
- Wind threshold `> 90` (not `≥ 90`): 90.0 km/h classifies as `"minor"`.
- Wind threshold `> 60` (not `≥ 60`): 60.0 km/h classifies as `"ok"`.
- Two minor flags at the same point escalate to `"moderate"`, not `"minor"`.
- A `"severe"` flag overrides any number of `"minor"` flags at the same point.
