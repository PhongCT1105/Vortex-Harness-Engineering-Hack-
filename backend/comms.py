"""Comms Agent — see docs/API_CONTRACT.md §3.

Sends a Slack message for an action. Uses a Slack incoming webhook if
SLACK_WEBHOOK_URL is configured, else falls back to a printed mock. Never
raises — failures are reported via `sent: false`.
"""

import httpx

from config import get_key

SLACK_CHANNEL_DEFAULT = "slack#procurement"


def _format_body(action: dict) -> str:
    return (
        f"[StormOps] {action['action']} "
        f"(shipment {action['shipment_id']}, "
        f"${action['value_usd']:,}, risk {action['risk_score']})."
    )


def comms_agent(action: dict) -> dict:
    channel = get_key("SLACK_CHANNEL") or SLACK_CHANNEL_DEFAULT
    body = _format_body(action)
    webhook_url = get_key("SLACK_WEBHOOK_URL")

    if webhook_url:
        try:
            resp = httpx.post(webhook_url, json={"text": body}, timeout=10)
            resp.raise_for_status()
            return {"channel": channel, "sent": True, "body": body}
        except Exception:
            return {"channel": channel, "sent": False, "body": body}

    print(f"[mock comms -> {channel}] {body}")
    return {"channel": channel, "sent": False, "body": body}
