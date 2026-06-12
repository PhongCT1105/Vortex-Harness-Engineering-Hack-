"""StormOps orchestrator + FastAPI app — see docs/ARCHITECTURE.md and
docs/API_CONTRACT.md §5 for the pipeline and endpoint shapes.
"""

import hashlib
import hmac
import json
import time
import uuid
import asyncio

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import httpx

from clickhouse_log import log_event, read_events
from automation import run_real_weather_pipeline
from clickhouse_store import ensure_schema, is_available as clickhouse_is_available, reset_schema
from comms import action_required_alert, comms_agent
from config import AUTO_PIPELINE_ENABLED, AUTO_PIPELINE_RUN_ON_STARTUP, FRONTEND_ORIGIN, get_key, integration_status, set_keys
from ai_agent import orchestration_agent
from impact import impact_agent
from mitigation import mitigation_agent
from orchestration_chat import answer_incident_question
from supply_chain import DEFAULT_PRODUCT, active_product_name, default_supply_chain, parse_supply_chain_csv
from supply_chain_weather import (
    REFRESH_SECONDS,
    get_route_weather,
    get_supply_chain_weather,
    invalidate_supply_chain_weather,
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

    if pending_approval:
        alert_result = action_required_alert(pending_approval, incident_id)
        log_event("approval_alert_sent", alert_result, incident_id)

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
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_supply_chain_weather_refresh():
    ensure_schema()
    default_supply_chain(DEFAULT_PRODUCT)
    if AUTO_PIPELINE_ENABLED:
        asyncio.create_task(periodic_real_weather_pipeline(DEFAULT_PRODUCT))
    if AUTO_PIPELINE_ENABLED and AUTO_PIPELINE_RUN_ON_STARTUP:
        asyncio.create_task(
            asyncio.to_thread(
                run_real_weather_pipeline,
                DEFAULT_PRODUCT,
                False,
                "startup",
            )
        )


async def periodic_real_weather_pipeline(product: str = DEFAULT_PRODUCT) -> None:
    await asyncio.sleep(REFRESH_SECONDS)
    while True:
        try:
            await asyncio.to_thread(run_real_weather_pipeline, product, False, "scheduled_weather_fetch")
        except Exception as exc:
            log_event("automation_failed", {"product": product, "trigger_source": "scheduled_weather_fetch", "error": str(exc)})
        await asyncio.sleep(REFRESH_SECONDS)


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
    SLACK_SIGNING_SECRET: str | None = None
    BACKEND_PUBLIC_URL: str | None = None
    DASHBOARD_WEBHOOK_URL: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: str | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SUPPLIER_ALERT_EMAIL: str | None = None


@app.get("/")
def root():
    return {"status": "StormOps API running"}


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
    asyncio.create_task(
        asyncio.to_thread(
            run_real_weather_pipeline,
            product,
            True,
            "csv_upload",
        )
    )
    return chain


@app.post("/run")
def run(req: RunRequest):
    return run_pipeline(req.event, req.product)


@app.post("/automation/supply-chain/report")
def supply_chain_report(req: AutomationRequest):
    product_name = _product(req.product)
    return run_real_weather_pipeline(product_name, req.force_refresh, "manual")


@app.post("/approve")
def approve(req: ApproveRequest):
    action = req.action
    result = comms_agent(action)
    executed = {**action, "status": "approved", **result}
    log_event("action_executed", executed, action.get("incident_id"))
    return result


def _verify_slack_signature(body: bytes, headers) -> bool:
    secret = get_key("SLACK_SIGNING_SECRET")
    if not secret:
        # No signing secret configured — accept (mock/dev mode).
        return True

    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not timestamp or not signature:
        return False
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    digest = hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


@app.post("/slack/interactions")
async def slack_interactions(request: Request):
    """Handles button clicks from Slack messages (e.g. the "Approve" action)."""
    raw_body = await request.body()
    if not _verify_slack_signature(raw_body, request.headers):
        return JSONResponse({"error": "invalid signature"}, status_code=401)

    form = await request.form()
    payload = json.loads(form.get("payload", "{}"))

    if payload.get("type") != "block_actions":
        return JSONResponse({"ok": True})

    for click in payload.get("actions", []):
        if click.get("action_id") != "approve_action":
            continue

        try:
            value = json.loads(click.get("value", "{}"))
        except json.JSONDecodeError:
            continue

        action = value.get("action")
        incident_id = value.get("incident_id")
        if not action:
            continue

        result = comms_agent({**action, "status": "approved"})
        executed = {**action, "status": "approved", **result}
        log_event("action_executed", executed, incident_id)
        log_event(
            "approval_clicked_in_slack",
            {"action_id": action.get("id"), "user": payload.get("user", {}).get("username")},
            incident_id,
        )

        response_url = payload.get("response_url")
        if response_url:
            try:
                httpx.post(
                    response_url,
                    json={
                        "replace_original": True,
                        "text": (
                            f"✅ Approved by <@{payload.get('user', {}).get('id', 'someone')}> — "
                            f"{action['action']} (shipment {action['shipment_id']})"
                        ),
                    },
                    timeout=10,
                )
            except Exception:
                pass

    return JSONResponse({"ok": True})


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
