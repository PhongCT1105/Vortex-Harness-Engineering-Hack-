## 1. Dependencies

- [x] 1.1 Update `backend/requirements.txt`: remove `jua`, add `requests` explicitly, keep `python-dotenv`

## 2. Module Bootstrap

- [x] 2.1 Create `backend/open_meteo_connector.py` with imports (`math`, `requests`) and `load_dotenv()` at module top
- [x] 2.2 Define `BASE_URL = "https://api.open-meteo.com/v1/forecast"`
- [x] 2.3 Define `DEFAULT_VARIABLES` list with the three Jua-named threshold variables
- [x] 2.4 Define `VARIABLE_MAP` dict mapping each Jua variable name to its Open-Meteo equivalent
- [x] 2.5 Define severity threshold constants (`_WIND_SEVERE_KMH`, `_WIND_MINOR_KMH`, `_PRECIP_MINOR_MM_HR`, `_TEMP_MINOR_K`) with identical values to `jua_connector.py`

## 3. HTTP Error Handling

- [x] 3.1 Implement `_handle_http_error(response, context: str)`: raise `RuntimeError` with readable messages for HTTP 400, 404, 429, and 5xx; include context (lat/lon or bbox) in each message

## 4. Point Forecast

- [x] 4.1 Implement `get_forecast(lat, lon, variables, hours=24)`: merge `DEFAULT_VARIABLES`, translate to Open-Meteo names, compute `forecast_days = max(1, ceil(hours / 24))`, GET `BASE_URL`, call `_handle_http_error` on non-200 response
- [x] 4.2 In `get_forecast`: extract per-variable hourly arrays from the response, compute the worst-case value (max for wind/precip, min for temperature), convert temperature from °C to K, and return a dict shaped as `{"data_vars": {<jua_var>: {"data": <peak_value>}, ...}}`

## 5. Regional Forecast

- [x] 5.1 Implement `get_regional_forecast(bbox, variables, hours=24)`: validate `len(bbox) == 4` (raise `ValueError` if not), derive the 4 corner coordinates from `(min_lat, min_lon, max_lat, max_lon)`
- [x] 5.2 In `get_regional_forecast`: call `get_forecast` for each of the 4 corners, average the `data` value per variable across all 4 results (only when all 4 corners return data), return a dict in the same shape as `get_forecast`

## 6. Severity Classification and Route Scanner

- [x] 6.1 Copy `_classify_severity(conditions: dict) -> tuple[bool, str]` verbatim from `jua_connector.py` — no threshold or logic changes
- [x] 6.2 Implement `scan_route(waypoints, variables, hours=24)`: validate 5–10 waypoints, iterate sequentially calling `get_forecast`, classify severity, catch per-point exceptions returning `{lat, lon, flagged: False, severity: "unknown", error: "..."}`, return results in input order

## 7. Import Swap Documentation

- [x] 7.1 Add a comment at the top of `open_meteo_connector.py` with the one-line import change instruction: `# To switch from jua_connector: change 'from jua_connector import ...' to 'from open_meteo_connector import ...'`
