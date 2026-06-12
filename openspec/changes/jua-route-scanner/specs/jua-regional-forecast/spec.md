## ADDED Requirements

### Requirement: Regional bounding-box forecast retrieval
The module SHALL expose `get_regional_forecast(bbox: tuple[float, float, float, float], variables: list[str], hours: int = 24) -> dict` that queries the Jua SDK using the bounding box (`min_lat`, `min_lon`, `max_lat`, `max_lon`), `Models.EPT2`, and `init_time="latest"`, and returns forecast data as a dict. It SHALL raise `ValueError` if `bbox` does not contain exactly 4 float values.

#### Scenario: Successful regional forecast
- **WHEN** a valid 4-element float `bbox`, `variables`, and `hours` are provided
- **THEN** the function returns a dict containing regional forecast data

#### Scenario: Malformed bounding box
- **WHEN** `bbox` contains fewer or more than 4 values
- **THEN** the function raises `ValueError` describing the expected format

#### Scenario: SDK error during regional forecast
- **WHEN** the Jua SDK raises an exception
- **THEN** `get_regional_forecast` re-raises with a readable message identifying the bbox and the underlying error
