"""StormOps orchestrator + FastAPI app — see docs/ARCHITECTURE.md and
docs/API_CONTRACT.md §5 for the pipeline and endpoint shapes.
"""

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from clickhouse_log import EVENTS, log_event
from comms import comms_agent
from config import FRONTEND_ORIGIN, integration_status, set_keys
from impact import impact_agent
from mitigation import mitigation_agent
from weather import weather_agent


def run_pipeline(event_text: str) -> dict:
    incident_id = uuid.uuid4().hex[:8]

    weather = weather_agent(event_text)
    log_event("weather_detected", weather, incident_id)

    impact = impact_agent(weather)
    log_event("impact_assessed", impact, incident_id)

    actions = mitigation_agent(impact)
    log_event("actions_generated", actions, incident_id)

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
        "weather": weather,
        "impact": impact,
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


class RunRequest(BaseModel):
    event: str


class ApproveRequest(BaseModel):
    action: dict


class ConfigRequest(BaseModel):
    JUA_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
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


@app.post("/run")
def run(req: RunRequest):
    return run_pipeline(req.event)


@app.post("/approve")
def approve(req: ApproveRequest):
    action = req.action
    result = comms_agent(action)
    executed = {**action, "status": "approved", **result}
    log_event("action_executed", executed, action.get("incident_id"))
    return result


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
