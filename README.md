# StormOps

**Autonomous factory-ops agent for weather-driven supply-chain disruption.**

On a trigger, StormOps pulls a **real** weather forecast for supplier regions, reasons
over a supplier/shipment graph to score disruption risk, **auto-executes low-risk
mitigations**, **escalates high-risk ones to a human**, and fires the approved actions as
real Slack/email — every step logged. Built for the Harness Engineering Hack.

One-liner: *StormOps turns real-time extreme-weather signals into governed, human-approved
supply-chain mitigation actions across procurement, logistics, and factory ops.*

---

## Why this wins (maps to all 5 judging criteria, 20% each)
- **Idea** — real factory/procurement pain, not another chatbot.
- **Technical** — real weather data + a multi-agent reasoning pipeline.
- **Tool Use** — coherent story across Jua, Composio, OpenUI, Guild, Render.
- **Presentation** — one clean 3-min storm scenario.
- **Autonomy** — runs on a trigger over **real-time** data; **tiered autonomy** auto-acts
  on low-risk items and only escalates expensive ones. This is the criterion most teams
  fumble — lean on it hard.

## Architecture
```
NL/trigger event
   └─ Weather Agent   (Jua real forecast → wind/precip/temp/severity)
        └─ Impact Agent   (severity × criticality × urgency → at-risk shipments)
             └─ Mitigation Agent   (reroute / expedite / buffer)
                  ├─ low-risk  → auto-execute → Comms Agent (Composio: Slack/email)
                  └─ high-risk → human approval → Comms Agent
   all governed + triggered by Guild ; every event → ClickHouse ; UI via OpenUI ; deploy on Render
```

## Run (mock mode, zero keys)
```bash
cd backend && pip install -r requirements.txt
python main.py            # no-server smoke test, prints a full incident
uvicorn main:app --reload # API: POST /run {"event": "..."}, POST /approve, GET /events
```

---

## Demo-safe build order (do them in this order; you're shippable at every checkpoint)
1. **0:00–0:30 — Core loop (DONE in this repo).** `python main.py` already produces an
   incident with auto-executed + pending actions. You have a demo *now*.
2. **0:30–1:15 — Composio real Slack send.** Wire the block in `comms_agent`. Grab a key
   from the Composio DevRel. First *real action* = locks the Autonomy story + the $200.
3. **1:15–2:00 — OpenUI adaptive front-end.** `npx skills add thesysdev/openui` then have
   Claude Code scaffold an incident console that reads `/run` + `/events`. Make it
   **adaptive**: calm card for moderate, full red console for severe. ($2,000, few use it.)
4. **2:00–2:45 — Jua real weather.** `pip install jua`, key from Jua DevRel/CEO. Replace
   the mock in `weather_agent`. Now "acts on real-time data" is literally true. (Judge = CEO.)
5. **2:45–3:45 — Guild wrap + trigger.** Register the deployed app in Guild, run it on a
   schedule trigger, route `pending_approval` through Guild's HITL gate. ($2,800 headline.)
   If the SDK fights you, the web-UI + Render-deploy + schedule path still earns the prize.
6. **3:45–4:15 — Render deploy.** Push backend + frontend. (Free credits, easy mention.)
7. **4:15–4:30 — ClickHouse (if green).** Swap `log_event` to insert into `agent_events`,
   show the timeline in the UI. ($1,600, judges love observability.)
8. **Stretch — Airbyte.** Replace ONE mock pull with a real connector (e.g. procurement
   backlog from Linear/Jira). Only if everything above is solid. ($1,750.)

Cut order if behind: drop Airbyte, then ClickHouse, then Guild-SDK (keep Guild web-UI).
Never cut: Composio (real action) + the adaptive UI + the autonomy framing.

## The 3-minute demo script
1. Type: *"A massive storm front is hitting Central Europe."*
2. Weather Agent (Jua): Wind 92 km/h, Rain 47 mm, severity HIGH — **real forecast**.
3. Impact Agent: 3 suppliers affected, 3 shipments at risk, ranked by score.
4. Mitigation Agent: proposes reroute/expedite per shipment.
5. **Autonomy beat:** the $80k reroute **auto-executes** (Slack fires live via Composio);
   the $120k and $150k ones **pause for human approval**.
6. Click **Approve** on one → real Slack message sends.
7. Show the **Guild** trace + **ClickHouse** timeline: incident resolved, every action audited.
   Close: *"Jua sees the storm, the agent reasons about your supply chain, Composio acts,
   Guild governs, OpenUI adapts, Render runs it — autonomously, with a human gate on the
   expensive calls."*

## Keys to collect on-site (the DevRels are the speakers/judges)
- Composio — Slack/Gmail send
- Jua — weather API (X-API-Key)
- OpenUI/Thesys — C1 key if using the hosted GenUI engine
- Guild — workspace + (Python or TS) SDK access
- ClickHouse / Render — accounts
