"""Mitigation Agent — see docs/API_CONTRACT.md §3/§4.

Produces action dicts and tags each with requires_approval based on
AUTO_EXECUTE_USD_LIMIT (the tiered-autonomy threshold).
"""

import uuid

from config import AUTO_EXECUTE_USD_LIMIT


def mitigation_agent(impact: dict) -> list[dict]:
    actions = []
    for shipment in impact["shipments"]:
        if shipment["risk_score"] >= 0.7:
            action_text = (
                f"Switch {shipment['component'].lower()} order to backup "
                f"supplier {shipment['backup_supplier_id']}"
            )
        elif shipment["risk_score"] >= 0.5:
            action_text = f"Expedite shipment {shipment['shipment_id']} via air freight"
        else:
            action_text = f"Add 3-day buffer to shipment {shipment['shipment_id']}"

        actions.append(
            {
                "id": uuid.uuid4().hex[:8],
                "shipment_id": shipment["shipment_id"],
                "action": action_text,
                "value_usd": shipment["value_usd"],
                "risk_score": shipment["risk_score"],
                "requires_approval": shipment["value_usd"] >= AUTO_EXECUTE_USD_LIMIT,
            }
        )

    return actions
