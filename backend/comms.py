"""Comms Agent — see docs/API_CONTRACT.md §3.

Fans the AI's analysis out to every downstream channel an operator actually
acts on:

- Slack: actionable, severity-formatted alerts and reports (Block Kit).
- Supplier email: procurement-facing notices for actions that touch a
  supplier lane (e.g. "switch to backup supplier").
- Dashboard: a structured payload (via DASHBOARD_WEBHOOK_URL, or the same
  Airbyte-managed context-layer endpoint) so the live ops dashboard reflects
  the latest AI output.

Every dispatch is best-effort and never raises — failures are reported via
`sent: false` so the audit trail (ClickHouse, via clickhouse_log) still
records what was attempted.
"""

import json
import smtplib
from email.message import EmailMessage

import httpx

from config import get_key

SLACK_CHANNEL_DEFAULT = "slack#procurement"

# urgency/severity -> (emoji, Slack attachment color)
_SEVERITY_STYLE = {
    "normal": ("✅", "#2eb886"),
    "watch": ("👀", "#daa038"),
    "elevated": ("⚠️", "#daa038"),
    "high": ("🔥", "#e01e5a"),
    "urgent": ("🔥", "#e01e5a"),
    "critical": ("🚨", "#e01e5a"),
    "severe": ("🚨", "#e01e5a"),
}


def _style(level: str | None) -> tuple[str, str]:
    return _SEVERITY_STYLE.get((level or "normal").lower(), ("ℹ️", "#cccccc"))


def _format_body(action: dict) -> str:
    return (
        f"[StormOps] {action['action']} "
        f"(shipment {action['shipment_id']}, "
        f"${action['value_usd']:,}, risk {action['risk_score']})."
    )


def _action_blocks(action: dict, status: str, incident_id: str | None = None) -> list[dict]:
    emoji, _ = _style("critical" if action.get("risk_score", 0) >= 0.7 else "watch")
    status_label = {
        "auto_executed": "Auto-executed",
        "pending_approval": "Needs approval",
        "approved": "Approved & executed",
    }.get(status, status)
    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{emoji} *{status_label}* — {action['action']}\n"
                    f"Shipment `{action['shipment_id']}` · "
                    f"${action['value_usd']:,} · risk {action['risk_score']}"
                ),
            },
        }
    ]

    if status == "pending_approval":
        # Embed the action (+ incident id) in the button value so the Slack
        # interaction handler can approve it without the operator opening the dashboard.
        value = json.dumps({"incident_id": incident_id, "action": action})[:2000]
        blocks.append(
            {
                "type": "actions",
                "block_id": f"approve_{action.get('id', '')}",
                "elements": [
                    {
                        "type": "button",
                        "style": "primary",
                        "text": {"type": "plain_text", "text": "✅ Approve"},
                        "action_id": "approve_action",
                        "value": value,
                    }
                ],
            }
        )

    return blocks


def _post_slack(blocks: list[dict], fallback_text: str) -> dict:
    channel = get_key("SLACK_CHANNEL") or SLACK_CHANNEL_DEFAULT
    webhook_url = get_key("SLACK_WEBHOOK_URL")
    result = {"channel": channel, "sent": False}

    if not webhook_url:
        print(f"[mock slack -> {channel}] {fallback_text}")
        return result

    try:
        resp = httpx.post(webhook_url, json={"text": fallback_text, "blocks": blocks}, timeout=10)
        resp.raise_for_status()
        result["sent"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def comms_agent(action: dict) -> dict:
    """Send an actionable Slack alert for a single mitigation action."""
    body = _format_body(action)
    status = "approved" if action.get("status") == "approved" else "auto_executed"
    blocks = _action_blocks(action, status)
    result = _post_slack(blocks, body)
    result["body"] = body
    return result


def action_required_alert(actions: list[dict], incident_id: str | None = None) -> dict:
    """Send a Slack alert for actions that need human approval before they execute."""
    if not actions:
        return {"sent": False, "skipped": "no pending actions"}

    emoji, _ = _style("urgent")
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Action required — incident {incident_id or ''}"},
        },
        {"type": "divider"},
    ]
    for action in actions:
        blocks.extend(_action_blocks(action, "pending_approval", incident_id))

    total = sum(a["value_usd"] for a in actions)
    fallback = f"[StormOps] {len(actions)} action(s) need approval, total ${total:,}."
    result = _post_slack(blocks, fallback)
    result["body"] = fallback
    return result


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


def _report_blocks(report: dict) -> list[dict]:
    condition = report.get("current_condition", "normal")
    urgency = report.get("urgency", "normal")
    emoji, _ = _style(urgency if urgency != "normal" else condition)
    exposure = report.get("exposure_summary") or []
    actions = report.get("recommended_actions") or []

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} StormOps report — {report.get('product', 'unknown')}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Condition:* {condition}  ·  *Urgency:* {urgency}\n"
                    f"{report.get('executive_summary', 'No summary generated.')}"
                ),
            },
        },
    ]

    if exposure:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Exposure:*\n" + "\n".join(f"• {e}" for e in exposure[:5])},
            }
        )

    if actions:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Recommended actions:*\n" + "\n".join(f"• {a}" for a in actions[:5]),
                },
            }
        )

    if report.get("requires_human_attention"):
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "🔔 *This report requires human review before downstream actions are sent.*"},
            }
        )

    return blocks


def _send_supplier_email(subject: str, body: str) -> dict:
    """Email procurement/supplier contacts. SMTP if configured, else mock."""
    to_addr = get_key("SUPPLIER_ALERT_EMAIL")
    result = {"configured": False, "sent": False, "to": to_addr}

    if not to_addr:
        return result

    result["configured"] = True
    host = get_key("SMTP_HOST")
    from_addr = get_key("SMTP_FROM_EMAIL") or "stormops@example.com"

    if not host:
        print(f"[mock email -> {to_addr}] {subject}\n{body}")
        return result

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.set_content(body)

        port = int(get_key("SMTP_PORT") or "587")
        username = get_key("SMTP_USERNAME")
        password = get_key("SMTP_PASSWORD")

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        result["sent"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def supplier_email_agent(report: dict) -> dict:
    """Email procurement/suppliers when a report calls for supplier-facing action."""
    actions = report.get("recommended_actions") or []
    supplier_actions = [
        a for a in actions if any(k in a.lower() for k in ("supplier", "reroute", "backup", "expedite"))
    ]
    if not supplier_actions:
        return {"configured": False, "sent": False, "skipped": "no supplier-facing actions"}

    subject = f"[StormOps] {report.get('product', 'Supply chain')} — {report.get('urgency', 'normal')} action needed"
    body = (
        f"Condition: {report.get('current_condition', 'unknown')}\n\n"
        f"{report.get('executive_summary', '')}\n\n"
        "Requested actions:\n" + "\n".join(f"- {a}" for a in supplier_actions)
    )
    return _send_supplier_email(subject, body)


def _push_dashboard(report: dict) -> dict:
    """Push the latest AI report/context to the live dashboard via webhook."""
    url = get_key("DASHBOARD_WEBHOOK_URL") or get_key("AIRBYTE_REPORT_WEBHOOK_URL")
    result = {"configured": False, "sent": False}
    if not url:
        return result

    result["configured"] = True
    try:
        resp = httpx.post(url, json={"type": "stormops_report", "report": report}, timeout=10)
        resp.raise_for_status()
        result["sent"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def dispatch_report(report: dict) -> dict:
    """Fan out a supply-chain report to Slack, supplier email, and the dashboard.

    Every channel is independent and best-effort; the result captures what was
    attempted and what succeeded so it can be written to the audit trail.
    """
    body = _format_report(report)
    result = {
        "dashboard": _push_dashboard(report),
        "slack": {**_post_slack(_report_blocks(report), body), "channel": get_key("SLACK_CHANNEL") or SLACK_CHANNEL_DEFAULT},
        "supplier_email": supplier_email_agent(report),
        "body": body,
    }

    if not result["slack"]["sent"] and not result["dashboard"]["sent"] and not result["supplier_email"]["sent"]:
        print(f"[mock report -> {result['slack']['channel']}] {body}")

    return result
