"""StormOps orchestrator + FastAPI app — see docs/ARCHITECTURE.md and
docs/API_CONTRACT.md §5 for the pipeline and endpoint shapes.
"""

import uuid
import asyncio

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from clickhouse_log import EVENTS, log_event
from comms import comms_agent
from config import FRONTEND_ORIGIN, integration_status, set_keys
from ai_agent import orchestration_agent
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

    orchestration = orchestration_agent(event_text, weather, impact, actions, product_name)
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
    asyncio.create_task(periodic_supply_chain_weather_refresh(DEFAULT_PRODUCT))


class RunRequest(BaseModel):
    event: str
    product: str | None = None


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


@app.post("/approve")
def approve(req: ApproveRequest):
    action = req.action
    result = comms_agent(action)
    executed = {**action, "status": "approved", **result}
    log_event("action_executed", executed, action.get("incident_id"))
    return result


@app.post("/chat")
def chat(req: ChatRequest):
    return answer_incident_question(req.incident, req.question, EVENTS)


@app.get("/events")
def events():
    return EVENTS


@app.get("/config")
def get_config():
    return integration_status()


@app.post("/config")
def post_config(req: ConfigRequest):
    set_keys({k: v for k, v in req.model_dump().items() if v is not None})
    return integration_status()


if __name__ == "__main__":
    incident = run_pipeline("A massive storm front is hitting Central Europe.")
    import json

    print(json.dumps(incident, indent=2, default=str))
