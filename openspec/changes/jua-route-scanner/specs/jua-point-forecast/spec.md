## ADDED Requirements

### Requirement: Point forecast retrieval
The module SHALL expose `get_forecast(lat: float, lon: float, variables: list[str], hours: int = 24) -> dict` that queries the Jua SDK using `Models.EPT2` and `init_time="latest"` for the specified coordinate and variable list, and returns forecast data as a dict. The variables list MUST always include `wind_speed_at_height_level_10m`, `air_temperature_at_height_level_2m`, and `precipitation_amount_at_surface`; the function SHALL enforce this by merging them in if absent.

#### Scenario: Successful point forecast
- **WHEN** valid `lat`, `lon`, `variables`, and `hours` are provided
- **THEN** the function returns a dict containing forecast data for at least the three required variables

#### Scenario: Required variables auto-injected
- **WHEN** the caller passes a `variables` list that omits one or more of the three required variables
- **THEN** the function merges the missing variables in before querying the SDK

#### Scenario: SDK error
- **WHEN** the Jua SDK raises an exception during the query
- **THEN** `get_forecast` re-raises with a readable message identifying the lat/lon and the underlying error
