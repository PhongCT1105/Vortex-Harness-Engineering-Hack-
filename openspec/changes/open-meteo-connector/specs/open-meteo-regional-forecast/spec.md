## ADDED Requirements

### Requirement: Regional forecast via 4-corner averaging
The module SHALL expose `get_regional_forecast(bbox: tuple[float, float, float, float], variables: list[str], hours: int = 24) -> dict` that fetches point forecasts for all 4 corners of the bounding box `(min_lat, min_lon, max_lat, max_lon)` — i.e., `(min_lat, min_lon)`, `(min_lat, max_lon)`, `(max_lat, min_lon)`, `(max_lat, max_lon)` — and returns a dict in the same shape as `get_forecast`, with each variable's value being the arithmetic mean of the 4 corner values. It SHALL raise `ValueError` if `bbox` does not contain exactly 4 values.

#### Scenario: Successful regional forecast
- **WHEN** a valid 4-element `bbox`, `variables`, and `hours` are provided and all 4 corner calls succeed
- **THEN** the function returns a dict with per-variable values averaged across the 4 corners

#### Scenario: Malformed bbox
- **WHEN** `bbox` does not contain exactly 4 float values
- **THEN** the function raises `ValueError` describing the expected format

#### Scenario: One corner call fails
- **WHEN** one of the 4 corner GET requests fails with an HTTP error
- **THEN** the function raises `RuntimeError` with a message identifying the failing corner and the HTTP status

#### Scenario: Return shape matches point forecast
- **WHEN** `get_regional_forecast` completes successfully
- **THEN** the returned dict has the same `{"data_vars": {<jua_var>: {"data": <value>}}}` structure as `get_forecast`
