"""
StormOps — autonomous factory-ops agent for weather-driven supply-chain disruption.

Runs out of the box with ZERO API keys (mock weather + rule-based reasoning +
printed actions), so you always have a working demo. Each sponsor integration is
a clearly marked, isolated block you can switch on as you wire keys.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # then POST to /run  (see __main__ block for a no-server smoke test)

Pipeline:
    NL event -> Weather Agent -> Impact Agent -> Mitigation Agent -> (Guild gate) -> Comms Agent
"""

import csv
import os
import time
import uuid
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent

# High-risk actions (e.g. expensive reroutes) escalate to a human; everything
# else auto-executes. This tiered policy is what makes "autonomous on real-time
# data" true while keeping a human safety gate. Tune the threshold live in the demo.
AUTO_EXECUTE_USD_LIMIT = 100_000

CRITICALITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_csv(name: str) -> list[dict]:
    with open(DATA / name) as f:
        return list(csv.DictReader(f))


SUPPLIERS = load_csv("suppliers.csv")
SHIPMENTS = load_csv("shipments.csv")


# --------------------------------------------------------------------------- #
# AGENT 1 — Weather Agent:  natural language -> structured weather risk
# --------------------------------------------------------------------------- #
# Country centroids so we can fetch a real forecast per affected region.
COUNTRY_COORDS = {
    "Germany": (51.0, 10.0), "Austria": (47.5, 14.5), "Poland": (52.0, 19.0),
    "Spain": (40.0, -3.7), "Sweden": (62.0, 15.0), "Netherlands": (52.1, 5.3),
}
KNOWN_COUNTRIES = list(COUNTRY_COORDS)


def weather_agent(event_text: str) -> dict:
    """Parse a free-text event into {affected_countries, wind, precip, temp, severity}.

    Tries (1) Jua real forecast, then (2) Claude parsing, then (3) keyword fallback.
    """
    affected = [c for c in KNOWN_COUNTRIES if c.lower() in event_text.lower()]
    if not affected and "central europe" in event_text.lower():
        affected = ["Germany", "Austria", "Poland"]
    if not affected:
        affected = ["Germany"]  # demo default

    # ---- (1) JUA INTEGRATION (real-time data -> Autonomy criterion) --------- #
    # pip install jua ; key from the Jua DevRel on-site. X-API-Key header.
    # Confirm exact endpoint/fields with their docs (docs.jua.ai) — schema TODO.
    if os.getenv("JUA_API_KEY"):
        try:
            from jua import Jua  # type: ignore
            client = Jua(api_key=os.environ["JUA_API_KEY"])
            lat, lon = COUNTRY_COORDS[affected[0]]
            fc = client.weather.get_forecast(  # TODO: confirm method name w/ Jua docs
                model="ept-2", latitude=lat, longitude=lon,
                variables=["wind_speed", "precipitation", "temperature"],
            )
            wind = float(fc["wind_speed"]); precip = float(fc["precipitation"])
            temp = float(fc["temperature"])
            return _score_weather(affected, wind, precip, temp, source="jua")
        except Exception as e:  # never let a live API kill the demo
            print(f"[jua] falling back to mock: {e}")

    # ---- (2) Claude parsing (optional, nice severity reasoning) ------------- #
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            msg = anthropic.Anthropic().messages.create(
                model="claude-opus-4-8", max_tokens=300,
                messages=[{"role": "user", "content":
                    "Extract storm severity from this event as STRICT JSON with keys "
                    "wind_kmh, precip_mm, temp_c (numbers only). Event: " + event_text}],
            )
            import json, re
            raw = re.search(r"\{.*\}", msg.content[0].text, re.S).group()
            d = json.loads(raw)
            return _score_weather(affected, d["wind_kmh"], d["precip_mm"],
                                  d["temp_c"], source="claude")
        except Exception as e:
            print(f"[claude] falling back to mock: {e}")

    # ---- (3) Mock fallback — always works ---------------------------------- #
    return _score_weather(affected, wind=92, precip=47, temp=4, source="mock")


def _score_weather(countries, wind, precip, temp, source) -> dict:
    # crude 0-1 severity; tune in demo
    severity = min(1.0, (wind / 120) * 0.5 + (precip / 80) * 0.5)
    level = "severe" if severity > 0.7 else "high" if severity > 0.45 else "moderate"
    return {
        "affected_countries": countries, "wind_kmh": round(wind),
        "precipitation_mm": round(precip), "temperature_c": round(temp),
        "severity": round(severity, 2), "risk_level": level, "source": source,
    }


# --------------------------------------------------------------------------- #
# AGENT 2 — Impact Agent:  weather + supplier graph -> at-risk suppliers/shipments
# --------------------------------------------------------------------------- #
# ---- AIRBYTE INTEGRATION POINT (stretch) ----------------------------------- #
# To honestly target Airbyte ($1,750), replace ONE of these mock pulls with a
# real Airbyte Agent connector, e.g. pull the live procurement backlog from
# Linear/Jira:  `uv pip install airbyte-agent-sdk`, then wrap a connector as a
# tool. Don't pretend the CSV is Airbyte — point a real connector at a real system.
def impact_agent(weather: dict) -> dict:
    hit = set(weather["affected_countries"])
    suppliers = [s for s in SUPPLIERS if s["country"] in hit]
    sids = {s["supplier_id"] for s in suppliers}
    shipments = [sh for sh in SHIPMENTS if sh["supplier_id"] in sids]

    scored = []
    for sh in shipments:
        sup = next(s for s in SUPPLIERS if s["supplier_id"] == sh["supplier_id"])
        urgency = 1.0 if sh["status"] == "in_transit" else 0.6
        eta = max(int(sh["eta_days"]), 1)
        score = weather["severity"] * CRITICALITY_WEIGHT[sup["criticality"]] * urgency * (3 / eta)
        scored.append({
            "shipment_id": sh["shipment_id"], "supplier": sup["name"],
            "country": sup["country"], "component": sup["component"],
            "value_usd": int(sh["value_usd"]), "backup": sup["backup_supplier"],
            "risk_score": round(min(score, 1.0), 2),
        })
    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "affected_suppliers": len(suppliers),
        "at_risk_shipments": len(scored),
        "shipments": scored,
    }


# --------------------------------------------------------------------------- #
# AGENT 3 — Mitigation Agent:  at-risk items -> recommended actions
# --------------------------------------------------------------------------- #
def mitigation_agent(impact: dict) -> list[dict]:
    actions = []
    for sh in impact["shipments"]:
        if sh["risk_score"] < 0.3:
            continue
        if sh["backup"]:
            action = f"Switch {sh['component']} order to backup supplier {sh['backup']}"
        else:
            action = f"Expedite shipment {sh['shipment_id']} and add inventory buffer"
        actions.append({
            "id": str(uuid.uuid4())[:8],
            "shipment_id": sh["shipment_id"],
            "action": action,
            "value_usd": sh["value_usd"],
            "risk_score": sh["risk_score"],
            # tiered autonomy decision
            "requires_approval": sh["value_usd"] >= AUTO_EXECUTE_USD_LIMIT,
        })
    return actions


# --------------------------------------------------------------------------- #
# AGENT 4 — Comms Agent:  approved action -> real Slack/email via Composio
# --------------------------------------------------------------------------- #
def comms_agent(action: dict) -> dict:
    text = (f"[StormOps] {action['action']} "
            f"(shipment {action['shipment_id']}, ${action['value_usd']:,}, "
            f"risk {action['risk_score']}).")

    # ---- COMPOSIO INTEGRATION POINT (real action -> Autonomy $200) ---------- #
    # pip install composio_openai openai ; key from Composio DevRel on-site.
    # from composio import Composio
    # from composio_openai import OpenAIProvider
    # composio = Composio(provider=OpenAIProvider())
    # tools = composio.tools.get(user_id="default",
    #             tools=["SLACK_SEND_MESSAGE", "GMAIL_SEND_EMAIL"])
    # resp = openai.chat.completions.create(model="gpt-4.1", tools=tools,
    #             messages=[{"role":"user","content": f"Send this to #procurement: {text}"}])
    # result = composio.provider.handle_tool_calls(user_id="default", response=resp)
    if os.getenv("COMPOSIO_API_KEY"):
        # wire the block above; left mock so the repo runs key-free
        pass

    print(f"[comms] (mock send) {text}")
    return {"channel": "slack#procurement", "sent": True, "body": text}


# --------------------------------------------------------------------------- #
# ClickHouse event log (observability -> $1,600). Mock prints until wired.
# --------------------------------------------------------------------------- #
EVENTS: list[dict] = []  # also serve this list to the OpenUI timeline


def log_event(kind: str, payload: Any) -> None:
    EVENTS.append({"ts": time.time(), "kind": kind, "payload": payload})
    # ---- CLICKHOUSE INTEGRATION POINT ------------------------------------- #
    # import clickhouse_connect; client.insert("agent_events", [...]) — batch on shutdown.
    print(f"[event] {kind}")


# --------------------------------------------------------------------------- #
# Orchestrator (this is what Guild governs / triggers — see below)
# --------------------------------------------------------------------------- #
def run_pipeline(event_text: str) -> dict:
    incident = str(uuid.uuid4())[:8]
    weather = weather_agent(event_text); log_event("weather_detected", weather)
    impact = impact_agent(weather);       log_event("impact_assessed", impact)
    actions = mitigation_agent(impact);   log_event("actions_generated", actions)

    auto, pending = [], []
    for a in actions:
        if a["requires_approval"]:
            pending.append(a); log_event("approval_requested", a)
        else:
            comms_agent(a); a["status"] = "auto_executed"; auto.append(a)
            log_event("action_executed", a)

    return {
        "incident_id": incident, "weather": weather, "impact": impact,
        "auto_executed": auto, "pending_approval": pending,
    }


# ---- GUILD INTEGRATION ($2,800, headline prize) ---------------------------- #
# Guild wraps these agents to give you: multi-agent governance, the human-approval
# gate (pending_approval above), execution traces, cost tracking, and a TRIGGER so
# run_pipeline fires on a schedule = genuinely autonomous. Guild has a Python SDK;
# confirm maturity with Corbett Waddingham (Head of DevRel, on-site). The TS path:
#   import { llmAgent } from "@guildai/agents-sdk"
#   export default llmAgent({ description: "StormOps weather-ops agent", tools: {...} })
# Fastest demo path if the SDK fights you: deploy this app on Render, register it in
# Guild's web UI, and run it on a Guild schedule trigger.


# --------------------------------------------------------------------------- #
# FastAPI surface (optional import so core logic tests without the dep)
# --------------------------------------------------------------------------- #
try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="StormOps")

    class RunReq(BaseModel):
        event: str

    class ApproveReq(BaseModel):
        action: dict

    @app.post("/run")
    def run(req: RunReq):
        return run_pipeline(req.event)

    @app.post("/approve")
    def approve(req: ApproveReq):
        res = comms_agent(req.action)
        req.action["status"] = "human_approved"
        log_event("action_executed", req.action)
        return res

    @app.get("/events")
    def events():
        return EVENTS
except ImportError:
    app = None  # fine for the smoke test below


# --------------------------------------------------------------------------- #
# No-server smoke test:  python main.py
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import json
    out = run_pipeline("A massive storm front is hitting Central Europe.")
    print(json.dumps(out, indent=2))
