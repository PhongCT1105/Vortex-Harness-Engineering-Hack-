## Why

The existing `jua_connector.py` requires a paid Jua API account with grid/query-engine access; smoke tests confirm the current credentials only authenticate but cannot fetch forecasts (HTTP 403). Open-Meteo is a free, unauthenticated REST API that provides the same weather variables needed for route scanning — replacing the internals removes the credential dependency and unblocks all forecast functionality immediately.

## What Changes

- New file `backend/open_meteo_connector.py`: drop-in replacement exposing the identical three-function interface (`get_forecast`, `get_regional_forecast`, `scan_route`) implemented over plain HTTP with no SDK and no API key
- Updated `backend/requirements.txt`: remove `jua`, retain `requests` and `python-dotenv`
- One-line import swap documented for callers switching from `jua_connector` to `open_meteo_connector`
- `backend/jua_connector.py` is **not removed** — both files coexist during parallel testing

## Capabilities

### New Capabilities

- `open-meteo-point-forecast`: `get_forecast()` via GET to `https://api.open-meteo.com/v1/forecast` with lat/lon, hourly variable list, and `forecast_days` derived from `hours`; returns a normalized dict with the same structure callers already expect
- `open-meteo-regional-forecast`: `get_regional_forecast()` by fetching all 4 corners of the bounding box and averaging per-variable values; same return shape as the point forecast
- `open-meteo-route-scan`: `scan_route()` with identical waypoint bounds (5–10), per-point failure isolation, output ordering, and severity classification logic copied verbatim from the Jua connector

### Modified Capabilities

_(none — this change adds a new file; existing `jua_connector.py` is untouched)_

## Impact

- **Dependencies**: `jua` removed from `requirements.txt`; `requests` added (already a transitive dep via jua, now explicit)
- **Callers**: any file importing from `jua_connector` needs one import line changed to `open_meteo_connector`
- **Auth/env**: no `JUA_KEY_ID` or `JUA_SECRET` required; `.env.example` remains valid but unused by the new connector
- **Breaking**: none — function signatures and return shapes are preserved exactly
