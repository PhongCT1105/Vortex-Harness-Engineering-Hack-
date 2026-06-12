## 1. Dependencies & Environment

- [x] 1.1 Add `jua` and `python-dotenv` to `backend/requirements.txt`
- [x] 1.2 Create `backend/.env.example` with `JUA_KEY_ID=` and `JUA_SECRET=` as empty placeholders

## 2. Module Bootstrap

- [x] 2.1 Create `backend/jua_connector.py` with `load_dotenv()` at module level and required imports (`os`, `jua`, `python-dotenv`)
- [x] 2.2 Define `DEFAULT_VARIABLES` constant containing the three required variable names

## 3. Authentication & Error Handling

- [x] 3.1 Implement `authenticate()`: read `JUA_KEY_ID` and `JUA_SECRET`, raise `ValueError` naming any missing var, return authenticated Jua SDK client
- [x] 3.2 Implement `_handle_http_error(status_code, ...)` helper that maps 400/401/402/403 to readable exception messages

## 4. Forecast Functions

- [x] 4.1 Implement `get_forecast(lat, lon, variables, hours=24)`: merge in `DEFAULT_VARIABLES` if absent, call SDK with `Models.EPT2` + `init_time="latest"`, return dict, wrap SDK errors with readable message including lat/lon
- [x] 4.2 Implement `get_regional_forecast(bbox, variables, hours=24)`: validate bbox is 4-float tuple (raise `ValueError` if not), call SDK with bounding box + `Models.EPT2` + `init_time="latest"`, return dict, wrap SDK errors with readable message

## 5. Route Scanner

- [x] 5.1 Implement `_classify_severity(conditions: dict) -> tuple[bool, str]`: apply all five threshold rules and return `(flagged, severity)` using the escalation priority chain (severe > moderate > minor > ok)
- [x] 5.2 Implement `scan_route(waypoints, variables, hours=24)`: validate waypoint count is 5–10 (raise `ValueError` otherwise), iterate waypoints sequentially calling `get_forecast()`, catch per-point exceptions and return `{lat, lon, flagged: False, severity: "unknown", error: "..."}` for failures, return results in input order

## 6. Usage Example

- [x] 6.1 Add 5-line `# Example` comment block at the bottom of `jua_connector.py` demonstrating `authenticate()` + `scan_route()` with an 8-waypoint Hamburg → Munich route
