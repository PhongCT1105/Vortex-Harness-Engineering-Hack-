## Context

The backend has no weather data source. Downstream ETA prediction and contingency generation need per-waypoint weather conditions along a route. The Jua AI Python SDK (`jua`) provides NWP forecasts via EPT2; authentication uses an `X-API-Key: {JUA_KEY_ID}:{JUA_SECRET}` header. We are adding a single connector module (`jua_connector.py`) with four public functions.

## Goals / Non-Goals

**Goals:**
- Authenticated Jua SDK client construction from env vars, failing fast on missing credentials
- Point forecast and regional (bounding-box) forecast retrieval via SDK
- Route scanning: sequential per-waypoint forecasts with threshold-based severity classification and graceful per-point failure isolation
- Explicit handling of HTTP 400/401/402/403 errors with readable messages

**Non-Goals:**
- Parallel/async waypoint fetching
- Caching, rate-limit backoff, or retry logic
- Any data transformation beyond extracting the dict from the SDK response
- Unit or integration tests

## Decisions

**`authenticate()` returns the SDK client; forecast functions call it internally**
Rationale: keeps the public API stateless and simple. Callers do not manage client lifetime. Each forecast function constructs a fresh client, which is acceptable given no retry/caching requirements.

**Severity escalation via explicit priority rules, not a scoring matrix**
Rationale: the threshold table maps cleanly to a priority chain: any `severe` variable → `"severe"`; two or more `minor` flags → `"moderate"`; one `minor` → `"minor"`; none → `"ok"`. A numeric score would obscure the business logic without adding expressiveness.

**Per-point failures return `{flagged: False, severity: "unknown", error: "..."}` and do not abort the scan**
Rationale: a single bad waypoint (transient network error, invalid coordinate) must not invalidate the entire route scan. Callers inspect the `error` field to decide how to handle missing points.

**Waypoint count clamped to 5–10 with `ValueError` on violation**
Rationale: below 5 is likely a miscall (not a route); above 10 would create unacceptably slow sequential scanning with no retry budget. Both bounds are enforced at the start of `scan_route`.

**Default variables list always includes the three threshold variables**
Rationale: `wind_speed_at_height_level_10m`, `air_temperature_at_height_level_2m`, and `precipitation_amount_at_surface` are required for severity evaluation; omitting them would silently produce incorrect results.

**No raw `requests` calls; SDK throughout**
Rationale: SDK manages auth header construction (`X-API-Key: {KEY_ID}:{SECRET}`) and endpoint routing. Using it directly prevents header format drift and couples us only to the SDK contract, not the raw HTTP API.

## Risks / Trade-offs

- **SDK bounding-box API surface unknown at design time** → verify `get_regional_forecast` parameter names against SDK docs before implementing; adjust if the bbox argument form differs from assumed tuple unpacking.
- **`init_time="latest"` may not be a valid SDK kwarg** → confirm against SDK docs; omit if not supported and document the assumption.
- **Sequential scanning is slow for 10 waypoints** → acceptable for v1; callers should expect latency proportional to waypoint count × per-call latency.
- **Threshold values are hardcoded** → intentional per spec; changing them requires a code change, not config.
- **SDK exception types not fully known** → wrap all SDK calls in broad `Exception` catch for the per-point failure path; refine to specific exception types once SDK internals are confirmed.
