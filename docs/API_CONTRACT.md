# API Contract — build against this, not each other's code

All shapes below are the **exact** dicts/JSON already used in `main.py`. If your
module returns this shape, it drops into the pipeline with zero changes elsewhere.

---

## 1. Weather Agent (Person A — Jua)

**Function:** `weather_agent(event_text: str) -> dict`

**Output:**
```json
{
  "affected_countries": ["Germany", "Austria", "Poland"],
  "wind_kmh": 92,
  "precipitation_mm": 47,
  "temperature_c": 4,
  "severity": 0.72,
  "risk_level": "severe",
  "source": "jua"
}
```
- `affected_countries`: must be a subset of `COUNTRY_COORDS` keys in `main.py`
  (`Germany, Austria, Poland, Spain, Sweden, Netherlands`) — these are the
  countries present in `suppliers.csv`.
- `severity`: float 0–1. `risk_level`: `"moderate" | "high" | "severe"`.
- `source`: `"jua" | "claude" | "mock"` — purely informational, shown in UI/logs.
- **Real Jua call**: replace the body of `weather_agent` (or the `if
  os.getenv("JUA_API_KEY")` block) — keep `_score_weather()` as the shared
  normalizer so severity scoring stays consistent.
- On any exception, fall back to mock (`_score_weather(affected, 92, 47, 4,
  source="mock")`) — never raise out of this function.

---

## 2. ClickHouse Event Log (Person A)

**Function:** `log_event(kind: str, payload: Any) -> None`

**Event kinds emitted by the pipeline (fixed set, do not rename):**
`weather_detected`, `impact_assessed`, `actions_generated`, `approval_requested`,
`action_executed`

**Row shape to insert into ClickHouse table `agent_events`:**
```json
{
  "ts": 1750000000.123,
  "incident_id": "a1b2c3d4",
  "kind": "action_executed",
  "payload": { "...": "kind-specific dict, JSON-encode as string column" }
}
```
- `ts`: unix float (already provided).
- `incident_id`: **not currently passed into `log_event`** — Person A should add
  an `incident_id: str | None = None` param to `log_event` and thread it through
  (Person C will pass it from `run_pipeline`, which already generates `incident`).
  Keep the param optional with default `None` so existing calls don't break.
- Table schema suggestion: `(ts Float64, incident_id String, kind String, payload
  String, INDEX ... ) ENGINE = MergeTree ORDER BY ts`.
- Keep `EVENTS` in-memory list working too — frontend's `/events` endpoint reads
  from it. ClickHouse insert is **additive**, not a replacement.

---

## 3. Comms Agent (Person B — Airbyte Slack connector)

**Function:** `comms_agent(action: dict) -> dict`

**Input** (`action`, one entry from `mitigation_agent` output):
```json
{
  "id": "f3a9c1d2",
  "shipment_id": "SH2",
  "action": "Switch aluminum frame order to backup supplier S5",
  "value_usd": 80000,
  "risk_score": 0.81,
  "requires_approval": false
}
```

**Output (must match this shape — frontend and ClickHouse read it):**
```json
{
  "channel": "slack#procurement",
  "sent": true,
  "body": "[StormOps] Switch aluminum frame order to backup supplier S5 (shipment SH2, $80,000, risk 0.81)."
}
```
- Build the Slack message text from `action` fields (format shown above is the
  current convention — keep it, the frontend log renders `body` directly).
- Replace the body of `comms_agent` with the real Airbyte Slack connector call.
  On failure, fall back to the existing `print(...)` + return the same shape with
  `"sent": false` — **never raise**, the orchestrator does not catch exceptions
  from this function.
- `channel` can be hardcoded (`"slack#procurement"`) or made configurable via env
  var `SLACK_CHANNEL` — either is fine, just keep the key name `channel`.

---

## 4. Impact + Mitigation Agents (Person C — already implemented)

No action needed from A/B. Documented here so you know what feeds your module:

- `impact_agent(weather: dict) -> dict` — consumes Weather Agent output exactly as
  shaped in §1.
- `mitigation_agent(impact: dict) -> list[dict]` — produces the `action` dicts
  shaped in §3.

---

## 5. Orchestrator output (`run_pipeline`) — what the frontend consumes

```json
{
  "incident_id": "a1b2c3d4",
  "weather": { "...": "shape from §1" },
  "impact": { "affected_suppliers": 3, "at_risk_shipments": 3, "shipments": [ "..." ] },
  "auto_executed": [ "...action dicts with status='auto_executed', plus comms result merged in" ],
  "pending_approval": [ "...action dicts with status omitted until approved" ]
}
```

## Endpoints (already in `main.py`, frontend builds against these)
- `POST /run` `{"event": "<free text>"}` -> orchestrator output above.
- `POST /approve` `{"action": <one pending_approval dict>}` -> comms result (§3),
  also appends an `action_executed` event.
- `GET /events` -> list of `{ts, kind, payload}` (in-memory `EVENTS`).
- `GET /supply-chain/weather` -> cached weather intelligence for every country and
  supplier-to-assembly route in the active supplier graph. Uploaded CSVs become
  the active graph in memory. Query params:
  - `product`: optional product label. If omitted, uses the latest uploaded product
    or `Electric Vehicle`.
  - `force_refresh=true`: bypasses the 4-hour cache and pulls fresh provider data.
- `GET /supply-chain/weather/routes` -> route-only weather. Query params:
  - `product`: optional product label.
  - `supplier_id`: optional supplier lane filter, e.g. `S1`.

### Supply-chain weather output
```json
{
  "product": "Electric Vehicle",
  "generated_at": "2026-06-12T18:00:00+00:00",
  "expires_at": "2026-06-12T22:00:00+00:00",
  "refresh_seconds": 14400,
  "source": "open-meteo+weatherapi+wttr+duckduckgo",
  "worst_risk_level": "normal",
  "max_severity": 0.07,
  "countries": [
    {
      "country": "Germany",
      "supplier_count": 2,
      "components": ["Battery cells"],
      "value_usd": 200000,
      "avg_criticality": 0.9,
      "wind_kmh": 12.1,
      "precipitation_mm": 0.0,
      "temperature_c": 21.3,
      "severity": 0.07,
      "risk_level": "normal",
      "provider_readings": [{ "source": "open-meteo", "wind_kmh": 12.1 }],
      "context": "Germany is at normal supply-chain weather risk...",
      "search": {
        "source": "rules",
        "query": "",
        "summary": "Current numeric weather is normal; no live disruption search was needed.",
        "results": []
      }
    }
  ],
  "routes": [
    {
      "supplier_id": "S1",
      "component": "Steel chassis",
      "country": "Germany",
      "destination": { "city": "Wolfsburg", "country": "Germany" },
      "max_severity": 0.07,
      "worst_risk_level": "normal",
      "worst_point": "Steel chassis origin - Germany",
      "context": "Steel chassis from Germany to Wolfsburg has normal route weather risk..."
    }
  ]
}
```

Claude orchestration receives two internal weather tools:
- `get_supply_chain_weather_intelligence`: full country + route monitor, cached for
  4 hours unless `force_refresh` is true.
- `lookup_route_weather`: route-only lookup for all lanes or one `supplier_id`.

## Env vars (no coordination needed — each person owns theirs)
| Var | Owner | Purpose |
|---|---|---|
| `JUA_API_KEY` | A | real weather |
| `WEATHERAPI_KEY` | C | optional free-tier backup weather provider |
| `CLICKHOUSE_*` (host/user/password/db) | A | event log sink |
| `AIRBYTE_*` / `SLACK_*` | B | Slack send via Airbyte |
| `ANTHROPIC_API_KEY` | C (optional) | Claude-based weather parsing fallback |
| `SUPPLY_CHAIN_WEATHER_REFRESH_HOURS` | C | Supply-chain weather cache cadence; default `4` |

All keys optional — missing key = mock path = pipeline still runs end-to-end.
