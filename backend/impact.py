"""Impact Agent — see docs/API_CONTRACT.md §4.

Consumes Weather Agent output and ranks at-risk shipments using suppliers.csv.
"""

from pathlib import Path

import pandas as pd

SUPPLIERS_CSV = Path(__file__).parent / "suppliers.csv"


def impact_agent(weather: dict) -> dict:
    suppliers = pd.read_csv(SUPPLIERS_CSV)
    affected = suppliers[suppliers["country"].isin(weather["affected_countries"])]

    severity = weather["severity"]
    shipments = []
    for _, row in affected.iterrows():
        risk_score = round(min(1.0, severity * row["criticality"] + 0.1), 2)
        shipments.append(
            {
                "shipment_id": row["shipment_id"],
                "supplier_id": row["supplier_id"],
                "backup_supplier_id": row["backup_supplier_id"],
                "country": row["country"],
                "component": row["component"],
                "value_usd": int(row["value_usd"]),
                "criticality": float(row["criticality"]),
                "risk_score": risk_score,
            }
        )

    shipments.sort(key=lambda s: s["risk_score"], reverse=True)

    return {
        "affected_suppliers": affected["supplier_id"].nunique(),
        "at_risk_shipments": len(shipments),
        "shipments": shipments,
    }
