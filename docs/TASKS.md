# Task Breakdown

Each person works on a separate file/branch and merges into `main.py` via the
contracts in [API_CONTRACT.md](./API_CONTRACT.md). Merge order doesn't matter —
every module has a working mock, so partial merges never break the demo.

## Person A — Jua weather + ClickHouse (top layer)
1. Implement real `weather_agent` Jua call (replace TODO block in `main.py`,
   §1 of API_CONTRACT). Keep `_score_weather()` as the normalizer.
2. Add `incident_id` param to `log_event`, thread through to `EVENTS` entries.
3. Add `clickhouse_log.py`: connect via `clickhouse-connect`, create
   `agent_events` table if missing, insert on every `log_event` call (best-effort,
   never raise — wrap in try/except like the Jua call).
4. Smoke test: `python main.py` still prints a full incident with `source: "jua"`.

## Person B — Airbyte Slack connector
1. Implement real `comms_agent` (replace mock block in `main.py`, §3 of
   API_CONTRACT). Use Airbyte Agent SDK / connector to send to Slack.
2. Keep the return shape exactly `{channel, sent, body}` — frontend renders `body`.
3. On error, return `{"sent": false, ...}` instead of raising.
4. Smoke test: call `comms_agent({...sample action from §3...})` standalone and
   confirm a real Slack message lands.

## Person C (you) — glue + frontend
1. Wire `incident_id` through `run_pipeline` -> `log_event` once Person A adds the
   param (small one-line change per call site).
2. Build the `halyard/` frontend against `/run`, `/approve`, `/events` (§5):
   - Incident view: weather summary, ranked shipments, action list.
   - Auto-executed vs pending-approval sections, with an **Approve** button
     calling `POST /approve`.
   - Live audit log component (`LiveAuditLog.tsx` already scaffolded) reading
     `GET /events`.
3. Adaptive layout: calm card for `risk_level: moderate`, full alert console for
   `severe` (OpenUI integration point).
4. Deploy backend + frontend to Render once A/B modules are merged.
5. Optional: Guild wrap around `run_pipeline` for scheduled trigger + HITL gate.

## Integration checkpoints
- **Checkpoint 1**: each module passes its own standalone smoke test (mock or
  real) independently.
- **Checkpoint 2**: merge all three into `main.py`, run `python main.py` — full
  incident prints with real weather (A), real Slack send for auto-executed items
  (B), and ClickHouse rows written (A).
- **Checkpoint 3**: frontend hits the live backend end-to-end, including the
  Approve flow.
