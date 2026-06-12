"""StormOps orchestrator + FastAPI app — see docs/ARCHITECTURE.md and
docs/API_CONTRACT.md §5 for the pipeline and endpoint shapes.
"""

import uuid
import asyncio

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from clickhouse_log import log_event, read_events
from clickhouse_store import ensure_schema, get_weather_snapshot, is_available as clickhouse_is_available, reset_schema
from comms import comms_agent, dispatch_report
from config import FRONTEND_ORIGIN, integration_status, set_keys
from ai_agent import orchestration_agent, supply_chain_report_agent
from impact import impact_agent
from mitigation import mitigation_agent
from orchestration_chat import answer_incident_question
from supply_chain import DEFAULT_PRODUCT, active_product_name, default_supply_chain, parse_supply_chain_csv
from supply_chain_weather import (
    get_route_weather,
    get_supply_chain_weather,
    invalidate_supply_chain_weather,
    periodic_supply_chain_weather_refresh,
    refresh_supply_chain_weather,
)
from weather import weather_agent


def _product(product: str | None = None) -> str:
    return product or active_product_name()


def run_pipeline(event_text: str, product: str | None = None) -> dict:
    incident_id = uuid.uuid4().hex[:8]
    product_name = _product(product)

    weather = weather_agent(event_text)
    log_event("weather_detected", weather, incident_id)

    impact = impact_agent(weather, product_name)
    log_event("impact_assessed", impact, incident_id)

    actions = mitigation_agent(impact)
    log_event("actions_generated", actions, incident_id)

    try:
        supply_weather = get_supply_chain_weather(product_name, force_refresh=True)
        log_event(
            "supply_chain_weather_checked",
            {
                "product": supply_weather.get("product"),
                "generated_at": supply_weather.get("generated_at"),
                "worst_risk_level": supply_weather.get("worst_risk_level"),
                "max_severity": supply_weather.get("max_severity"),
                "country_count": len(supply_weather.get("countries", [])),
                "route_count": len(supply_weather.get("routes", [])),
            },
            incident_id,
        )
    except Exception as exc:
        log_event(
            "supply_chain_weather_check_failed",
            {"product": product_name, "error": str(exc)},
            incident_id,
        )

    orchestration = orchestration_agent(event_text, weather, impact, actions, product_name, incident_id)
    log_event("ai_orchestration_completed", orchestration, incident_id)

    auto_executed = []
    pending_approval = []

    for action in actions:
        if action["requires_approval"]:
            log_event("approval_requested", action, incident_id)
            pending_approval.append(action)
        else:
            comms_result = comms_agent(action)
            executed = {**action, "status": "auto_executed", **comms_result}
            log_event("action_executed", executed, incident_id)
            auto_executed.append(executed)

    return {
        "incident_id": incident_id,
        "product": product_name,
        "weather": weather,
        "impact": impact,
        "orchestration": orchestration,
        "auto_executed": auto_executed,
        "pending_approval": pending_approval,
    }


app = FastAPI(title="StormOps")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_supply_chain_weather_refresh():
    ensure_schema()
    default_supply_chain(DEFAULT_PRODUCT)
    asyncio.create_task(periodic_supply_chain_weather_refresh(DEFAULT_PRODUCT))


class RunRequest(BaseModel):
    event: str
    product: str | None = None


class AutomationRequest(BaseModel):
    product: str | None = None
    force_refresh: bool = False


class ApproveRequest(BaseModel):
    action: dict


class ChatRequest(BaseModel):
    question: str
    incident: dict


class ConfigRequest(BaseModel):
    JUA_API_KEY: str | None = None
    JUA_FORECAST_URL: str | None = None
    WEATHERAPI_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_MODEL: str | None = None
    ACTIVE_MODEL: str | None = None
    CLICKHOUSE_HOST: str | None = None
    CLICKHOUSE_PORT: str | None = None
    CLICKHOUSE_USER: str | None = None
    CLICKHOUSE_PASSWORD: str | None = None
    CLICKHOUSE_DATABASE: str | None = None
    AIRBYTE_API_KEY: str | None = None
    AIRBYTE_REPORT_WEBHOOK_URL: str | None = None
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_CHANNEL: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/supply-chain")
def get_supply_chain(product: str | None = None):
    return default_supply_chain(_product(product))


@app.get("/supply-chain/weather")
def supply_chain_weather(product: str | None = None, force_refresh: bool = False):
    return get_supply_chain_weather(_product(product), force_refresh)


@app.get("/supply-chain/weather/routes")
def supply_chain_route_weather(product: str | None = None, supplier_id: str | None = None):
    return get_route_weather(_product(product), supplier_id)


@app.post("/supply-chain/upload")
async def upload_supply_chain(file: UploadFile = File(...), product: str = Form(DEFAULT_PRODUCT)):
    content = await file.read()
    chain = parse_supply_chain_csv(content, product)
    invalidate_supply_chain_weather(product)
    asyncio.create_task(asyncio.to_thread(refresh_supply_chain_weather, product))
    return chain


@app.post("/run")
def run(req: RunRequest):
    return run_pipeline(req.event, req.product)


@app.post("/automation/supply-chain/report")
def supply_chain_report(req: AutomationRequest):
    automation_id = uuid.uuid4().hex[:8]
    product_name = _product(req.product)
    log_event(
        "automation_started",
        {"automation_id": automation_id, "product": product_name, "force_refresh": req.force_refresh},
        automation_id,
    )

    chain = default_supply_chain(product_name)
    fresh_snapshot = None if req.force_refresh else get_weather_snapshot(product_name, require_fresh=True)

    if fresh_snapshot is not None:
        weather_snapshot = fresh_snapshot
        log_event(
            "weather_snapshot_reused",
            {
                "automation_id": automation_id,
                "product": product_name,
                "generated_at": weather_snapshot.get("generated_at"),
                "expires_at": weather_snapshot.get("expires_at"),
            },
            automation_id,
        )
    else:
        weather_snapshot = get_supply_chain_weather(product_name, force_refresh=True)
        log_event(
            "weather_snapshot_refreshed",
            {
                "automation_id": automation_id,
                "product": product_name,
                "generated_at": weather_snapshot.get("generated_at"),
                "expires_at": weather_snapshot.get("expires_at"),
                "worst_risk_level": weather_snapshot.get("worst_risk_level"),
                "max_severity": weather_snapshot.get("max_severity"),
            },
            automation_id,
        )

    report = supply_chain_report_agent(product_name, chain, weather_snapshot, automation_id)
    log_event("automation_report_generated", report, automation_id)

    dispatch = dispatch_report(report)
    log_event("automation_report_dispatched", dispatch, automation_id)

    return {
        "automation_id": automation_id,
        "product": product_name,
        "weather_source": "clickhouse_cached" if fresh_snapshot is not None else "refreshed",
        "weather_generated_at": weather_snapshot.get("generated_at"),
        "report": report,
        "dispatch": dispatch,
    }


@app.post("/approve")
def approve(req: ApproveRequest):
    action = req.action
    result = comms_agent(action)
    executed = {**action, "status": "approved", **result}
    log_event("action_executed", executed, action.get("incident_id"))
    return result


@app.post("/chat")
def chat(req: ChatRequest):
    return answer_incident_question(req.incident, req.question, read_events())


@app.get("/events")
def events():
    return read_events()


@app.post("/admin/clickhouse/reset")
def reset_clickhouse():
    ok = reset_schema()
    if ok:
        default_supply_chain(DEFAULT_PRODUCT)
        invalidate_supply_chain_weather(DEFAULT_PRODUCT)
    return {"ok": ok}


@app.get("/config")
def get_config():
    status = integration_status()
    status["clickhouse"] = clickhouse_is_available()
    return status


@app.post("/config")
def post_config(req: ConfigRequest):
    set_keys({k: v for k, v in req.model_dump().items() if v is not None})
    status = integration_status()
    status["clickhouse"] = clickhouse_is_available()
    return status


if __name__ == "__main__":
    incident = run_pipeline("A massive storm front is hitting Central Europe.")
    import json

    print(json.dumps(incident, indent=2, default=str))
