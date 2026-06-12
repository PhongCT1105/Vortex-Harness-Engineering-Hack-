"""Impact Agent — see docs/API_CONTRACT.md §4.

Consumes Weather Agent output and ranks at-risk shipments using the active
supply-chain graph. Uploaded CSVs become the active graph in supply_chain.py.
"""

from supply_chain import DEFAULT_PRODUCT, default_supply_chain


def impact_agent(weather: dict, product: str = DEFAULT_PRODUCT) -> dict:
    chain = default_supply_chain(product)
    affected = [node for node in chain["nodes"] if node["country"] in weather["affected_countries"]]

    severity = weather["severity"]
    shipments = []
    for index, row in enumerate(affected, start=1):
        risk_score = round(min(1.0, severity * row["criticality"] + 0.1), 2)
        shipments.append(
            {
                "shipment_id": row.get("shipment_id") or f"SH{index}",
                "supplier_id": row["id"],
                "backup_supplier_id": row.get("backup_supplier_id") or f"B{index}",
                "country": row["country"],
                "component": row["component"],
                "value_usd": int(row["value_usd"]),
                "criticality": float(row["criticality"]),
                "risk_score": risk_score,
            }
        )

    shipments.sort(key=lambda s: s["risk_score"], reverse=True)

    return {
        "affected_suppliers": len({row["id"] for row in affected}),
        "at_risk_shipments": len(shipments),
        "shipments": shipments,
    }
