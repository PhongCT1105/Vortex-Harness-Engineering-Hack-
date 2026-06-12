# StormOps — Final Architecture (Source of Truth)

This document is the locked design for the hackathon build. All three workstreams
build against the **contracts in [API_CONTRACT.md](./API_CONTRACT.md)**, not against
each other's code. As long as your module's input/output JSON matches the contract,
you can build and test it in isolation and it will plug into `main.py` without
coordination calls.

## One-liner
StormOps turns real-time extreme-weather signals into governed, human-approved
supply-chain mitigation actions, with every step logged for audit.

## Pipeline (unchanged from `main.py`, now with owners)

```
   NL/trigger event
        │
        ▼
 ┌──────────────────┐
 │ Weather Agent     │  Person A (Jua + ClickHouse)
 │ (Jua real forecast)│  -> structured weather JSON
 └──────────────────┘
        │
        ▼
 ┌──────────────────┐
 │ Impact Agent      │  Person C (glue/orchestration)
 │ (supplier graph)  │  -> at-risk shipments, ranked
 └──────────────────┘
        │
        ▼
 ┌──────────────────┐
 │ Mitigation Agent  │  Person C
 │ (reroute/expedite)│  -> actions + tiered autonomy flag
 └──────────────────┘
        │
   ┌────┴─────┐
   ▼          ▼
 low-risk   high-risk
 auto-exec  -> human approval (frontend) -> approved
   │                                          │
   └─────────────┬────────────────────────────┘
                  ▼
          ┌──────────────────┐
          │ Comms Agent       │  Person B (Airbyte Slack connector)
          │ (Slack via Airbyte)│  -> delivery receipt
          └──────────────────┘

Every step -> log_event() -> ClickHouse (Person A) -> shown in frontend timeline (Person C)
```

## Workstream ownership

| Owner | Scope | Files |
|---|---|---|
| **Person A** | Jua weather integration + ClickHouse event logging | `backend/weather.py`, `backend/clickhouse_log.py` |
| **Person B** | Airbyte-based Slack connector (comms/delivery) | `backend/comms.py` |
| **Person C (you)** | Orchestration, impact/mitigation logic, FastAPI glue, frontend (`halyard/`), deploy | `backend/main.py`, `backend/impact.py`, `backend/mitigation.py`, `halyard/*` |

## Why this split works
- Each person's module is a **pure function** with a fixed input/output shape (see
  API_CONTRACT.md). No shared state, no import-order dependencies.
- Every module has a **mock fallback** already in `main.py` — if Person A's Jua key
  isn't ready, the mock weather still flows through the whole pipeline. Same for
  Slack/Airbyte. The demo never breaks.
- The orchestrator (`run_pipeline` in `main.py`) is the only place that calls all
  three modules — that's Person C's job, and it's already written.

## Tiered autonomy (the core "Autonomy" judging story)
- `AUTO_EXECUTE_USD_LIMIT = 100_000` in `main.py`. Actions below this auto-fire
  through the Comms Agent. Actions at/above it land in `pending_approval` and wait
  for a human click in the frontend (`POST /approve`).
- This is what makes both "acts autonomously on real-time data" AND "human governs
  high-stakes actions" true simultaneously. Do not remove the threshold split.

## Deploy target
Render, single backend service (`uvicorn main:app`) + Next.js frontend (`halyard/`).
Both already scaffolded.
