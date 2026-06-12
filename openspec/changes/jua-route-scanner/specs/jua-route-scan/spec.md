## ADDED Requirements

### Requirement: Waypoint count validation
`scan_route` SHALL raise `ValueError` if the `waypoints` list contains fewer than 5 or more than 10 entries, before making any SDK calls.

#### Scenario: Too few waypoints
- **WHEN** `waypoints` has fewer than 5 entries
- **THEN** `scan_route` raises `ValueError` stating the minimum is 5

#### Scenario: Too many waypoints
- **WHEN** `waypoints` has more than 10 entries
- **THEN** `scan_route` raises `ValueError` stating the maximum is 10

#### Scenario: Valid waypoint count
- **WHEN** `waypoints` has 5–10 entries
- **THEN** `scan_route` proceeds without raising

### Requirement: Sequential per-waypoint forecast and severity classification
`scan_route(waypoints: list[tuple[float, float]], variables: list[str], hours: int = 24) -> list[dict]` SHALL call `get_forecast()` for each waypoint in order, evaluate conditions against hardcoded thresholds, and return a list of result dicts in the same order as the input. Each successful result SHALL contain `lat`, `lon`, `conditions` (dict), `flagged` (bool), and `severity` (str).

Severity classification rules (applied to the maximum value across the forecast horizon for each variable):
- `wind_speed_at_height_level_10m > 90 km/h` → flag as `"severe"`
- `wind_speed_at_height_level_10m > 60 km/h` → flag as `"minor"`
- `precipitation_amount_at_surface > 10 mm/hr` → flag as `"minor"`
- `air_temperature_at_height_level_2m < 268 K` → flag as `"minor"`
- Any `"severe"` flag at a point → point severity is `"severe"`
- Two or more `"minor"` flags at the same point → point severity is `"moderate"`
- Exactly one `"minor"` flag → point severity is `"minor"`
- No flags → point severity is `"ok"`, `flagged` is `False`
- Any flagged point → `flagged` is `True`

#### Scenario: No thresholds exceeded
- **WHEN** all forecast values at a waypoint are within thresholds
- **THEN** the result for that point has `flagged: False` and `severity: "ok"`

#### Scenario: Single minor threshold exceeded
- **WHEN** exactly one minor threshold is exceeded at a waypoint
- **THEN** the result has `flagged: True` and `severity: "minor"`

#### Scenario: Two minor thresholds exceeded
- **WHEN** two or more minor thresholds are exceeded at the same waypoint
- **THEN** the result has `flagged: True` and `severity: "moderate"`

#### Scenario: Severe wind threshold exceeded
- **WHEN** wind speed exceeds 90 km/h at a waypoint
- **THEN** the result has `flagged: True` and `severity: "severe"`

#### Scenario: Output order preserved
- **WHEN** `scan_route` is called with N waypoints
- **THEN** the returned list has exactly N entries in the same order as the input

### Requirement: Graceful per-point failure isolation
If `get_forecast()` raises for a waypoint, `scan_route` SHALL catch the exception, continue processing remaining waypoints, and include `{lat, lon, flagged: False, severity: "unknown", error: "<message>"}` for the failed point at its original position.

#### Scenario: Single waypoint forecast fails
- **WHEN** `get_forecast()` raises an exception for one waypoint
- **THEN** that point's result contains `flagged: False`, `severity: "unknown"`, and a non-empty `error` string
- **THEN** all other waypoints are still processed and returned

#### Scenario: All other waypoints succeed despite one failure
- **WHEN** one waypoint fails and the rest succeed
- **THEN** the returned list length equals the input waypoint count and only the failed entry has `severity: "unknown"`
