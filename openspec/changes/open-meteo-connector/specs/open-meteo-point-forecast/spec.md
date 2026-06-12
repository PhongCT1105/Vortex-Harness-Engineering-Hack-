## ADDED Requirements

### Requirement: Point forecast via Open-Meteo HTTP GET
The module SHALL expose `get_forecast(lat: float, lon: float, variables: list[str], hours: int = 24) -> dict` that issues a GET request to `https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude`, `hourly` (translated variable names), and `forecast_days` (derived as `ceil(hours / 24)`, minimum 1). It SHALL return a dict shaped as `{"data_vars": {<jua_var_name>: {"data": <value>}, ...}}` using the original caller-facing Jua variable names as keys. Temperature SHALL be converted from °C to K before being stored in the return dict. The three default variables (`wind_speed_at_height_level_10m`, `air_temperature_at_height_level_2m`, `precipitation_amount_at_surface`) SHALL always be included regardless of what the caller passes.

#### Scenario: Successful point forecast
- **WHEN** valid `lat`, `lon`, `variables`, and `hours` are provided and the Open-Meteo API returns HTTP 200
- **THEN** the function returns a dict containing at least the three default variables under `data_vars`, with temperature in Kelvin

#### Scenario: Default variables auto-injected
- **WHEN** the caller passes `variables=[]`
- **THEN** all three default variables are requested and returned

#### Scenario: HTTP 400 from Open-Meteo
- **WHEN** the API returns HTTP 400
- **THEN** `get_forecast` raises `RuntimeError` with a message indicating bad request parameters and the lat/lon context

#### Scenario: HTTP 404 from Open-Meteo
- **WHEN** the API returns HTTP 404
- **THEN** `get_forecast` raises `RuntimeError` with a message indicating the endpoint was not found

#### Scenario: HTTP 429 from Open-Meteo
- **WHEN** the API returns HTTP 429
- **THEN** `get_forecast` raises `RuntimeError` with a message indicating rate limit exceeded

#### Scenario: HTTP 5xx from Open-Meteo
- **WHEN** the API returns any 5xx status code
- **THEN** `get_forecast` raises `RuntimeError` with a message indicating a server-side error and the status code

### Requirement: Variable name translation
The module SHALL maintain a mapping from Jua variable names to Open-Meteo variable names and translate in both directions: outbound requests use Open-Meteo names; the returned dict uses Jua names as keys.

| Jua name | Open-Meteo name |
|---|---|
| `wind_speed_at_height_level_10m` | `windspeed_10m` |
| `air_temperature_at_height_level_2m` | `temperature_2m` |
| `precipitation_amount_at_surface` | `precipitation` |

#### Scenario: Caller receives Jua-named keys
- **WHEN** `get_forecast` is called with the default variables
- **THEN** the returned dict contains keys `wind_speed_at_height_level_10m`, `air_temperature_at_height_level_2m`, and `precipitation_amount_at_surface` — not the Open-Meteo names
