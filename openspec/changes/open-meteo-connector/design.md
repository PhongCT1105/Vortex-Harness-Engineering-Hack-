## Context

`jua_connector.py` is unusable with current credentials — the account authenticates but returns HTTP 403 on all forecast queries (requires a paid grid-access tier). Open-Meteo is a free, open-access NWP REST API with no auth, no SDK, and no rate-limit for reasonable usage. The three public functions (`get_forecast`, `get_regional_forecast`, `scan_route`) must keep identical signatures and return shapes so callers need only change one import line.

## Goals / Non-Goals

**Goals:**
- `open_meteo_connector.py` with identical public API to `jua_connector.py`
- Variable name translation: Jua names → Open-Meteo names, and back in the returned dict
- `get_regional_forecast` approximated by averaging 4-corner point forecasts
- All HTTP errors (400, 404, 429, 5xx) surfaced as `RuntimeError` with readable messages
- `requirements.txt` updated: `jua` removed, `requests` made explicit

**Non-Goals:**
- Modifying `jua_connector.py` or its callers
- Async or parallel HTTP calls
- Caching or retry logic
- Changing severity thresholds or escalation logic in `scan_route`

## Decisions

**Plain `requests` over any HTTP client library**
Rationale: `requests` is already a transitive dependency (via `jua`). Making it explicit in `requirements.txt` adds nothing new to the environment. Avoids introducing `httpx` or `aiohttp` without need.

**Variable translation via a bidirectional mapping dict**
Rationale: Open-Meteo uses different names (`windspeed_10m`, `temperature_2m`, `precipitation`) from the Jua names callers pass in. A single `VARIABLE_MAP` constant makes the translation explicit and auditable. The returned dict uses the caller-facing Jua names so callers see no difference.

**`forecast_days` derived as `ceil(hours / 24)`, minimum 1**
Rationale: Open-Meteo's API takes `forecast_days` (integer days), not an hour count. Rounding up ensures the full requested horizon is covered. The returned data is then sliced to exactly `hours` time steps before peak extraction.

**`get_regional_forecast` approximated by 4-corner averaging**
Rationale: Open-Meteo has no native bounding-box query; it only accepts a single lat/lon point. Fetching the 4 corners and averaging is the simplest approximation that stays within the no-SDK, plain-HTTP constraint. The design doc for the Jua connector already noted that regional queries are approximated.

**Return dict shape matches `_extract_peak_conditions` output used by `scan_route`**
Rationale: `scan_route` calls `get_forecast` and then passes the result to `_extract_peak_conditions`, which reads `forecast_data["data_vars"][var]["data"]`. The Open-Meteo response is shaped differently; `get_forecast` MUST normalize it into this same nested structure so `scan_route` needs no changes.

**`scan_route` threshold logic copied verbatim**
Rationale: the spec explicitly prohibits changes to severity levels. Copy-paste from `jua_connector.py` with no modifications.

## Risks / Trade-offs

- **4-corner averaging is a rough approximation** → acceptable for route hazard flagging; a production system would use a grid-based approach
- **Open-Meteo variable units may differ from Jua** → temperature from Open-Meteo is in °C, not K; the connector MUST convert to K before passing to `_classify_severity` (threshold is 268 K)
- **`forecast_days` max is 16 for free tier** → `hours > 384` will be clamped; document in code
- **No retry logic** → transient 5xx surfaces immediately as `RuntimeError`; acceptable for v1
