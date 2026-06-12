# Jua Weather Connector

`jua_connector.py` provides weather forecast access via the Jua AI SDK. It exposes three public functions: a point forecast, a regional (bounding-box) forecast, and a route scanner that flags hazardous conditions along a sequence of waypoints.

---

## Setup

**Install dependencies:**

```bash
pip install jua python-dotenv
```

**Configure credentials** by copying `.env.example` and filling in your Jua API key:

```bash
cp .env.example .env
```

```
JUA_KEY_ID=your-key-id
JUA_SECRET=your-secret
```

Credentials are loaded automatically at import time via `python-dotenv`. In production environments where env vars are already set, `.env` is ignored.

---

## Functions

### `authenticate() -> JuaClient`

Reads `JUA_KEY_ID` and `JUA_SECRET` from the environment and returns an authenticated Jua SDK client. Raises `ValueError` immediately if either variable is missing or empty.

You do not need to call this directly — `get_forecast` and `get_regional_forecast` call it internally. It is exposed for startup validation or testing.

```python
from jua_connector import authenticate

client = authenticate()  # raises ValueError if credentials are missing
```

---

### `get_forecast(lat, lon, variables, hours=24) -> dict`

Fetches a point forecast for a single coordinate using the EPT2 model.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `lat` | `float` | Latitude (-90 to 90) |
| `lon` | `float` | Longitude (-180 to 180) |
| `variables` | `list[str]` | Weather variables to request. The three threshold variables are always included automatically (see below). |
| `hours` | `int` | Forecast horizon in hours. Default: `24`. |

**Always-included variables** (merged in automatically regardless of what you pass):
- `wind_speed_at_height_level_10m`
- `air_temperature_at_height_level_2m`
- `precipitation_amount_at_surface`

**Returns:** xarray dataset serialized as a dict (via `.to_xarray().to_dict()`). Data variables are nested under the `"data_vars"` key.

**Raises:** `RuntimeError` with a readable message on any SDK or network error.

```python
from jua_connector import get_forecast

data = get_forecast(lat=48.14, lon=11.58, variables=[], hours=24)
# data["data_vars"]["wind_speed_at_height_level_10m"] → forecast array
```

---

### `get_regional_forecast(bbox, variables, hours=24) -> dict`

Fetches a forecast over a geographic bounding box using the EPT2 model.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `bbox` | `tuple[float, float, float, float]` | `(min_lat, min_lon, max_lat, max_lon)` |
| `variables` | `list[str]` | Weather variables to request. Threshold variables are always included. |
| `hours` | `int` | Forecast horizon in hours. Default: `24`. |

**Returns:** xarray dataset serialized as a dict, same structure as `get_forecast`.

**Raises:**
- `ValueError` if `bbox` does not contain exactly 4 values.
- `RuntimeError` on any SDK or network error.

```python
from jua_connector import get_regional_forecast

# Germany bounding box
data = get_regional_forecast(
    bbox=(47.3, 6.0, 55.1, 15.0),
    variables=[],
    hours=48,
)
```

---

### `scan_route(waypoints, variables, hours=24) -> list[dict]`

Scans weather conditions along a route by fetching a point forecast for each waypoint sequentially, then classifying the severity of conditions at each point.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `waypoints` | `list[tuple[float, float]]` | Ordered list of `(lat, lon)` pairs. Must contain 5–10 entries. |
| `variables` | `list[str]` | Additional variables beyond the three defaults. Pass `[]` for defaults only. |
| `hours` | `int` | Forecast horizon per waypoint. Default: `24`. |

**Raises:** `ValueError` if `waypoints` has fewer than 5 or more than 10 entries.

**Returns:** A list of dicts in the same order as `waypoints`. Each entry is one of:

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

**Failed point** (Jua call raised an exception):
```python
{
    "lat": float,
    "lon": float,
    "flagged": False,
    "severity": "unknown",
    "error": "readable error message",
}
```

A single failed waypoint does not abort the scan — remaining waypoints are still processed.

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

All SDK errors are caught and re-raised as `RuntimeError` with a message that identifies the HTTP status code and the affected coordinate or bbox:

| HTTP status | Error message pattern |
|---|---|
| 401 | `Jua authentication failed (...): invalid or missing API credentials` |
| 403 | `Jua request forbidden (...): account lacks access to this resource` |
| 400 / credit limit | `Jua quota or billing issue (...): request exceeds credit limit` |
| 400 (other) | `Jua bad request (...): malformed request parameters` |
| 402 | `Jua payment required (...): quota or billing issue` |

---

## Full example: Hamburg → Munich route scan

```python
from jua_connector import authenticate, scan_route

# Validate credentials at startup (optional but recommended)
authenticate()

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

**Example output:**
```
  [53.55, 10.0] OK — severity: ok
  [53.2, 10.4] OK — severity: ok
  [52.8, 10.9] FLAGGED — severity: minor
  [52.4, 11.5] OK — severity: ok
  [52.1, 12.1] OK — severity: ok
  [51.6, 12.4] OK — severity: ok
  [51.0, 11.6] FLAGGED — severity: moderate
  [48.14, 11.58] OK — severity: ok
```
