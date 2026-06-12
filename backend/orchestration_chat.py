"""Incident follow-up chat for orchestration results.

This keeps the operator in the loop after Jua/weather, impact, mitigation, and
ClickHouse/audit data return. The response is deterministic so the demo works
without an LLM key, while the payload also includes OpenUI Lang that can be fed
to an OpenUI renderer later.
"""


def _money(value: int | float) -> str:
    return f"${int(value):,}"


def _risk_label(score: float) -> str:
    if score >= 0.7:
        return "critical"
    if score >= 0.5:
        return "elevated"
    return "watch"


def _match_question(question: str) -> str:
    normalized = question.lower()
    if any(term in normalized for term in ["damage", "damaged", "broken", "impact", "where"]):
        return "damage"
    if any(term in normalized for term in ["why", "reason", "because", "jua", "weather"]):
        return "reason"
    if any(term in normalized for term in ["action", "mitigation", "do", "approve", "next"]):
        return "action"
    if any(term in normalized for term in ["clickhouse", "audit", "log", "trace"]):
        return "audit"
    return "summary"


def build_openui_lang(incident: dict, question: str, audit_count: int) -> str:
    weather = incident["weather"]
    shipments = incident["impact"]["shipments"][:4]
    auto_count = len(incident.get("auto_executed", []))
    approval_count = len(incident.get("pending_approval", []))

    lines = [
        "root = IncidentPromptWindow(header, map, response, nextSteps)",
        (
            f'header = IncidentHeader("Incident {incident["incident_id"]}", '
            f'"{weather["risk_level"].upper()} weather risk from {weather["source"]}", '
            f'"{question}")'
        ),
        "map = SupplyChainMap([origin, lanes, factory])",
        (
            f'origin = SupplyNode("Weather zone", "{", ".join(weather["affected_countries"])}", '
            f'"damaged", "Wind {weather["wind_kmh"]} km/h · rain {weather["precipitation_mm"]} mm")'
        ),
        (
            f'lanes = SupplyNode("Supplier lane", "{len(shipments)} shipments at risk", '
            f'"damaged", "Top risk {shipments[0]["risk_score"] if shipments else 0}")'
        ),
        (
            f'factory = SupplyNode("Factory plan", "{auto_count} auto actions · {approval_count} approvals", '
            f'"recovering", "Audit events {audit_count}")'
        ),
        'response = DamageSummary("Affected components", [items])',
    ]

    if shipments:
        item_lines = []
        for index, shipment in enumerate(shipments):
            ident = f"item{index + 1}"
            item_lines.append(ident)
            lines.append(
                f'{ident} = DamageItem("{shipment["component"]}", "{shipment["country"]}", '
                f'"{_risk_label(float(shipment["risk_score"]))}", "{_money(shipment["value_usd"])}")'
            )
        lines[-(len(shipments) + 1)] = f'response = DamageSummary("Affected components", [{", ".join(item_lines)}])'
    else:
        lines.append('items = DamageItem("No active shipment damage", "All lanes", "watch", "$0")')

    lines.append(
        'nextSteps = NextBestActions(["Ask why this was classified as high risk", '
        '"Review approval-required actions", "Show ClickHouse audit trail"])'
    )
    return "\n".join(lines)


def answer_incident_question(incident: dict, question: str, events: list[dict]) -> dict:
    weather = incident["weather"]
    impact = incident["impact"]
    shipments = impact["shipments"]
    auto = incident.get("auto_executed", [])
    pending = incident.get("pending_approval", [])
    incident_events = [event for event in events if event.get("incident_id") == incident["incident_id"]]
    orchestration = incident.get("orchestration") or {}
    mode = _match_question(question)

    top = shipments[0] if shipments else None
    damaged_parts = ", ".join(
        f"{s['component']} in {s['country']} ({_risk_label(float(s['risk_score']))})"
        for s in shipments[:3]
    )

    if mode == "damage":
        answer = (
            f"The damaged part of the supply chain is the supplier lane in "
            f"{', '.join(weather['affected_countries'])}. "
            f"{impact['at_risk_shipments']} shipments are exposed. "
            f"Top affected parts: {damaged_parts or 'none'}."
        )
    elif mode == "reason":
        answer = (
            f"Jua/weather classified the trigger as {weather['risk_level']} risk because wind is "
            f"{weather['wind_kmh']} km/h, precipitation is {weather['precipitation_mm']} mm, "
            f"and the combined severity score is {weather['severity']:.2f}. "
            f"That score is multiplied by supplier criticality to rank shipment damage."
        )
    elif mode == "action":
        answer = (
            f"The orchestrator already prepared {len(auto) + len(pending)} mitigations: "
            f"{len(auto)} auto-executed and {len(pending)} waiting for approval. "
            f"The highest priority is {top['component']} on shipment {top['shipment_id']} "
            f"with risk {top['risk_score']:.2f}." if top else
            "No mitigation is required because no at-risk shipments were found."
        )
    elif mode == "audit":
        answer = (
            f"ClickHouse/audit has {len(incident_events)} events for this incident. "
            "The expected trace is weather_detected, impact_assessed, actions_generated, "
            "then approval_requested or action_executed for each mitigation."
        )
    else:
        answer = (
            orchestration.get("executive_summary")
            or (
                f"Incident {incident['incident_id']} is a {weather['risk_level']} weather disruption "
                f"affecting {impact['affected_suppliers']} suppliers and "
                f"{impact['at_risk_shipments']} shipments. "
                f"The prompt window highlights the damaged supplier lane and the parts requiring action."
            )
        )

    return {
        "answer": answer,
        "openui_lang": build_openui_lang(incident, question, len(incident_events)),
        "suggested_questions": orchestration.get("operator_questions") or [
            "Which part of the supply chain is damaged?",
            "Why did Jua classify this as high risk?",
            "Which mitigations need approval?",
            "Show the ClickHouse audit trail.",
        ],
    }
