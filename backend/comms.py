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


def _format_report(report: dict) -> str:
    actions = report.get("recommended_actions") or []
    action_lines = "\n".join(f"- {action}" for action in actions[:5]) or "- Continue monitoring."
    return (
        f"[StormOps Daily Supply-Chain Report]\n"
        f"Product: {report.get('product', 'unknown')}\n"
        f"Condition: {report.get('current_condition', 'unknown')}\n"
        f"Urgency: {report.get('urgency', 'normal')}\n"
        f"Summary: {report.get('executive_summary', 'No summary generated.')}\n"
        f"Recommended actions:\n{action_lines}"
    )


def dispatch_report(report: dict) -> dict:
    """Send a supply-chain report to the configured downstream channel.

    If AIRBYTE_REPORT_WEBHOOK_URL is configured, it receives the structured report.
    Slack receives the human-readable message when SLACK_WEBHOOK_URL is configured.
    """
    body = _format_report(report)
    result = {
        "airbyte": {"configured": False, "sent": False},
        "slack": {"configured": False, "sent": False, "channel": get_key("SLACK_CHANNEL") or SLACK_CHANNEL_DEFAULT},
        "body": body,
    }

    airbyte_webhook = get_key("AIRBYTE_REPORT_WEBHOOK_URL")
    if airbyte_webhook:
        result["airbyte"]["configured"] = True
        try:
            resp = httpx.post(airbyte_webhook, json={"report": report, "text": body}, timeout=10)
            resp.raise_for_status()
            result["airbyte"]["sent"] = True
        except Exception as exc:
            result["airbyte"]["error"] = str(exc)
    elif get_key("AIRBYTE_API_KEY"):
        result["airbyte"]["configured"] = True
        result["airbyte"]["error"] = "AIRBYTE_API_KEY is set, but AIRBYTE_REPORT_WEBHOOK_URL is missing."

    slack_webhook = get_key("SLACK_WEBHOOK_URL")
    if slack_webhook:
        result["slack"]["configured"] = True
        try:
            resp = httpx.post(slack_webhook, json={"text": body}, timeout=10)
            resp.raise_for_status()
            result["slack"]["sent"] = True
        except Exception as exc:
            result["slack"]["error"] = str(exc)

    if not result["airbyte"]["sent"] and not result["slack"]["sent"]:
        print(f"[mock report -> {result['slack']['channel']}] {body}")

    return result
