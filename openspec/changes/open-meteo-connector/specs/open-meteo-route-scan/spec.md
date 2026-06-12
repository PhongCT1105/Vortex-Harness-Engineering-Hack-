## ADDED Requirements

### Requirement: Route scan with identical behaviour to jua_connector
The module SHALL expose `scan_route(waypoints: list[tuple[float, float]], variables: list[str], hours: int = 24) -> list[dict]` with behaviour identical to the Jua connector: waypoint count validated at 5–10 (raise `ValueError` otherwise), `get_forecast` called sequentially for each waypoint, per-point failures caught and returned as `{lat, lon, flagged: False, severity: "unknown", error: "<message>"}`, results returned in input order.

Severity thresholds (copied verbatim from jua_connector — SHALL NOT be modified):
- `wind_speed_at_height_level_10m > 90` → severe
- `wind_speed_at_height_level_10m > 60` → minor
- `precipitation_amount_at_surface > 10` → minor
- `air_temperature_at_height_level_2m < 268` → minor
- Two or more minor flags → moderate
- Any severe → severe

#### Scenario: All waypoints succeed
- **WHEN** all point forecasts succeed for a valid 5–10 waypoint list
- **THEN** returns a list of `{lat, lon, conditions, flagged, severity}` dicts in input order

#### Scenario: Too few waypoints
- **WHEN** fewer than 5 waypoints are provided
- **THEN** raises `ValueError` stating the minimum is 5

#### Scenario: Too many waypoints
- **WHEN** more than 10 waypoints are provided
- **THEN** raises `ValueError` stating the maximum is 10

#### Scenario: Per-point failure isolation
- **WHEN** one waypoint's `get_forecast` call raises an exception
- **THEN** that point's entry has `flagged: False`, `severity: "unknown"`, and a non-empty `error` string; all other waypoints are still processed

#### Scenario: Output order preserved
- **WHEN** `scan_route` completes with N waypoints
- **THEN** the returned list has exactly N entries whose `lat`/`lon` match the input waypoints in order

### Requirement: Temperature unit correction in severity classification
Because Open-Meteo returns temperature in °C and `get_forecast` converts to K before storing, the `_classify_severity` function SHALL compare against the 268 K threshold using the K value already stored in the conditions dict — no additional conversion in the classifier.

#### Scenario: Temperature below -5°C flagged correctly
- **WHEN** `air_temperature_at_height_level_2m` is 260 K (= −13 °C) in the conditions dict
- **THEN** `_classify_severity` returns `minor` for that variable
