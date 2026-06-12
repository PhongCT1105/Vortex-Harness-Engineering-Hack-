## Why

ETA prediction and contingency generation require per-waypoint weather awareness along a route. Without it, the system is blind to conditions (wind, precipitation, temperature) that materially affect transit time and safety. The Jua AI SDK provides high-accuracy NWP forecasts; this change wires it into a route-scanning capability that flags hazardous conditions at each waypoint and returns structured data ready for downstream processing.

## What Changes

- New file `backend/jua_connector.py`: authenticated Jua SDK client factory, point forecast, regional forecast, and route-scanning functions with threshold-based severity classification
- New file `backend/.env.example`: documents required env vars
- Updated `backend/requirements.txt`: adds `jua` and `python-dotenv`

## Capabilities

### New Capabilities

- `jua-auth`: Authenticated client construction from `JUA_KEY_ID` and `JUA_SECRET` env vars; fails fast with readable errors if credentials are missing or rejected
- `jua-point-forecast`: Point forecast retrieval by lat/lon using `Models.EPT2` and `init_time="latest"` for a configurable hour horizon
- `jua-regional-forecast`: Bounding-box forecast retrieval using Jua SDK's geo support, same model and horizon settings
- `jua-route-scan`: Sequential per-waypoint forecast scan (5–10 waypoints) with hardcoded severity thresholds, graceful per-point failure handling, and order-preserving results

### Modified Capabilities

_(none)_

## Impact

- **Dependencies**: adds `jua`, `python-dotenv` to `requirements.txt`
- **Environment**: requires `JUA_KEY_ID` and `JUA_SECRET` at runtime; authenticated via `X-API-Key: {KEY_ID}:{SECRET}` header
- **Downstream consumers**: `scan_route` output (`list[dict]` with `lat`, `lon`, `conditions`, `flagged`, `severity`) feeds ETA prediction and contingency generation modules
- **HTTP error surface**: 400, 401, 402, 403 from Jua API must be caught and surfaced with readable messages
- **Breaking**: none
