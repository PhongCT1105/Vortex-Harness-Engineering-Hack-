# Open-Meteo Weather Connector

`open_meteo_connector.py` provides weather forecast access via the [Open-Meteo](https://open-meteo.com) free API. No API key or authentication is required. It exposes three public functions: a point forecast, a regional (bounding-box) forecast, and a route scanner that flags hazardous conditions along a sequence of waypoints.

**Switching from `jua_connector`:** change any import line from:
```python
from jua_connector import get_forecast, get_regional_forecast, scan_route
```
to:
```python
from open_meteo_connector import get_forecast, get_regional_forecast, scan_route
```
Function signatures and return shapes are identical.

---

## Setup

**Install dependencies:**

```bash
pip install requests python-dotenv
```

No credentials required. No `.env` configuration needed.

---

## Functions

### `get_forecast(lat, lon, variables, hours=24) -> dict`

Fetches a point forecast for a single coordinate from the Open-Meteo API.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `lat` | `float` | Latitude (-90 to 90) |
| `lon` | `float` | Longitude (-180 to 180) |
| `variables` | `list[str]` | Additional weather variables to request. The three threshold variables are always included automatically. |
| `hours` | `int` | Forecast horizon in hours. Default: `24`. Maximum: `384` (16 days). |

**Always-included variables** (merged in regardless of what you pass):
- `wind_speed_at_height_level_10m` — peak value over the horizon, in km/h
- `air_temperature_at_height_level_2m` — minimum value over the horizon, in K
- `precipitation_amount_at_surface` — peak value over the horizon, in mm/hr

**Returns:** `{"data_vars": {<variable_name>: {"data": <peak_value>}, ...}}`

Each value is a single float representing the worst-case reading across the full forecast horizon (maximum for wind and precipitation; minimum for temperature). Temperature is stored in Kelvin.

**Raises:** `RuntimeError` with a readable message on any HTTP or network error.

> **Note:** `hours > 384` is silently clamped to 384 (16 days), the Open-Meteo free-tier maximum.

```python
from open_meteo_connector import get_forecast

data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
wind  = data["data_vars"]["wind_speed_at_height_level_10m"]["data"]   # km/h
temp  = data["data_vars"]["air_temperature_at_height_level_2m"]["data"]  # K
precip = data["data_vars"]["precipitation_amount_at_surface"]["data"]  # mm/hr
```

---

### `get_regional_forecast(bbox, variables, hours=24) -> dict`

Fetches a forecast over a geographic bounding box by querying each of the four corners and averaging the results.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `bbox` | `tuple[float, float, float, float]` | `(min_lat, min_lon, max_lat, max_lon)` |
| `variables` | `list[str]` | Additional variables to request. Threshold variables are always included. |
| `hours` | `int` | Forecast horizon in hours. Default: `24`. |

**Returns:** Same shape as `get_forecast`. Each variable's value is the arithmetic mean of the four corner values. If any corner returns no data for a variable (e.g. all-null response), that variable is omitted from the result rather than averaged over a partial set.

**Raises:**
- `ValueError` if `bbox` does not contain exactly 4 values.
- `RuntimeError` if any corner request fails.

```python
from open_meteo_connector import get_regional_forecast

# Germany bounding box
data = get_regional_forecast(
    bbox=(47.3, 6.0, 55.1, 15.0),
    variables=[],
    hours=48,
)
avg_wind = data["data_vars"]["wind_speed_at_height_level_10m"]["data"]
```

---

### `scan_route(waypoints, variables, hours=24) -> list[dict]`

Scans weather conditions along a route by fetching a point forecast for each waypoint sequentially and classifying the severity of conditions at each point.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `waypoints` | `list[tuple[float, float]]` | Ordered list of `(lat, lon)` pairs. Must contain 5–10 entries. |
| `variables` | `list[str]` | Additional variables beyond the three defaults. Pass `[]` for defaults only. |
| `hours` | `int` | Forecast horizon per waypoint. Default: `24`. |

**Raises:** `ValueError` if `waypoints` has fewer than 5 or more than 10 entries.

**Returns:** A list of dicts in the same order as the input waypoints. Each entry is one of:

**Successful point:**
```python
{
    "lat": float,
    "lon": float,
    "conditions": {
        "wind_speed_at_height_level_10m": float,      # km/h, peak over horizon
        "air_temperature_at_height_level_2m": float,  # K, minimum over horizon
        "precipitation_amount_at_surface": float,     # mm/hr, peak over horizon
    },
    "flagged": bool,
    "severity": "ok" | "minor" | "moderate" | "severe",
}
```

**Failed point** (request raised an exception):
```python
{
    "lat": float,
    "lon": float,
    "flagged": False,
    "severity": "unknown",
    "error": "readable error message",
}
```

A single failed waypoint does not abort the scan — remaining waypoints are still processed and returned in their original positions.

#### Severity classification

Each point is evaluated against these hardcoded thresholds using the worst-case value across the forecast horizon:

| Condition | Threshold | Flag |
|---|---|---|
| Wind speed | > 90 km/h | severe |
| Wind speed | > 60 km/h | minor |
| Precipitation | > 10 mm/hr | minor |
| Temperature | < 268 K (−5 °C) | minor |

Escalation priority (highest wins):
- Any `severe` flag → `"severe"`
- Two or more `minor` flags → `"moderate"`
- Exactly one `minor` flag → `"minor"`
- No flags → `"ok"`, `flagged: False`

---

## Error handling

All HTTP errors are caught and re-raised as `RuntimeError` with a message that identifies the status code and the affected coordinate or bbox:

| HTTP status | Error message pattern |
|---|---|
| 400 | `Open-Meteo bad request (...): malformed request parameters` |
| 404 | `Open-Meteo endpoint not found (...): check BASE_URL` |
| 429 | `Open-Meteo rate limit exceeded (...): too many requests` |
| 5xx | `Open-Meteo server error (...): HTTP <status>` |
| Network failure | `Open-Meteo network error (...): <exception>` |

---

## Full example: Hamburg → Munich route scan

```python
from open_meteo_connector import scan_route

# 8 waypoints from Hamburg to Munich
route = [
    (53.55, 10.00),  # Hamburg
    (53.20, 10.40),
    (52.80, 10.90),
    (52.40, 11.50),
    (52.10, 12.10),
    (51.60, 12.40),
    (51.00, 11.60),
    (48.14, 11.58),  # Munich
]

results = scan_route(route, variables=[], hours=24)

for point in results:
    if "error" in point:
        print(f"  [{point['lat']}, {point['lon']}] ERROR: {point['error']}")
    else:
        status = "FLAGGED" if point["flagged"] else "OK"
        print(f"  [{point['lat']}, {point['lon']}] {status} — severity: {point['severity']}")
```

**Example output (live, 2026-06-12):**
```
  [53.55, 10.0] OK — severity: ok
  [53.2, 10.4] OK — severity: ok
  [52.8, 10.9] OK — severity: ok
  [52.4, 11.5] OK — severity: ok
  [52.1, 12.1] OK — severity: ok
  [51.6, 12.4] OK — severity: ok
  [51.0, 11.6] OK — severity: ok
  [48.14, 11.58] OK — severity: ok
```
