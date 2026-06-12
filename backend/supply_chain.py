"""Supply Chain Agent — builds the data for the 3D globe view.

Takes either the bundled demo suppliers.csv or an uploaded CSV describing
where each component/resource for a product comes from, geocodes each
country to lat/lng, and returns a list of supplier nodes plus arcs pointing
to the final assembly plant.
"""

import io
import copy
from pathlib import Path

import pandas as pd

from clickhouse_store import get_latest_product, get_supply_chain, save_supply_chain

SUPPLIERS_CSV = Path(__file__).parent / "suppliers.csv"

# Rough country centroid coordinates — enough for a demo globe.
COUNTRY_COORDS = {
    "Germany": (51.1657, 10.4515),
    "Austria": (47.5162, 14.5501),
    "Poland": (51.9194, 19.1451),
    "Spain": (40.4637, -3.7492),
    "Netherlands": (52.1326, 5.2913),
    "Sweden": (60.1282, 18.6435),
    "France": (46.6034, 1.8883),
    "Italy": (41.8719, 12.5674),
    "United Kingdom": (55.3781, -3.4360),
    "UK": (55.3781, -3.4360),
    "Czech Republic": (49.8175, 15.4730),
    "Czechia": (49.8175, 15.4730),
    "Belgium": (50.5039, 4.4699),
    "Portugal": (39.3999, -8.2245),
    "Switzerland": (46.8182, 8.2275),
    "Norway": (60.4720, 8.4689),
    "Finland": (61.9241, 25.7482),
    "Denmark": (56.2639, 9.5018),
    "Romania": (45.9432, 24.9668),
    "Hungary": (47.1625, 19.5033),
    "Slovakia": (48.6690, 19.6990),
    "Turkey": (38.9637, 35.2433),
    "China": (35.8617, 104.1954),
    "Japan": (36.2048, 138.2529),
    "South Korea": (35.9078, 127.7669),
    "Taiwan": (23.6978, 120.9605),
    "India": (20.5937, 78.9629),
    "Vietnam": (14.0583, 108.2772),
    "Thailand": (15.8700, 100.9925),
    "Indonesia": (-0.7893, 113.9213),
    "Malaysia": (4.2105, 101.9758),
    "United States": (37.0902, -95.7129),
    "USA": (37.0902, -95.7129),
    "Mexico": (23.6345, -102.5528),
    "Canada": (56.1304, -106.3468),
    "Brazil": (-14.2350, -51.9253),
    "Chile": (-35.6751, -71.5430),
    "Australia": (-25.2744, 133.7751),
    "South Africa": (-30.5595, 22.9375),
    "Morocco": (31.7917, -7.0926),
    "Egypt": (26.8206, 30.8025),
}

# Final assembly plant for the demo product.
ASSEMBLY_PLANT = {
    "name": "Assembly Plant",
    "city": "Wolfsburg",
    "country": "Germany",
    "lat": 52.4257,
    "lng": 10.7865,
}

DEFAULT_PRODUCT = "Electric Vehicle"
ACTIVE_SUPPLY_CHAINS: dict[str, dict] = {}
ACTIVE_PRODUCT = DEFAULT_PRODUCT


def _coords_for_country(country: str):
    if not isinstance(country, str):
        return None
    key = country.strip()
    if key in COUNTRY_COORDS:
        return COUNTRY_COORDS[key]
    # case-insensitive fallback
    for name, coords in COUNTRY_COORDS.items():
        if name.lower() == key.lower():
            return coords
    return None


def _build_from_dataframe(df: pd.DataFrame, product: str) -> dict:
    nodes = []
    arcs = []
    unresolved = []

    for _, row in df.iterrows():
        country = str(row.get("country", "")).strip()
        coords = _coords_for_country(country)
        if coords is None:
            unresolved.append(country)
            continue

        lat, lng = coords
        supplier_id = str(row.get("supplier_id", "")) or f"S{len(nodes) + 1}"
        shipment_id = str(row.get("shipment_id", "")) or f"SH{len(nodes) + 1}"
        backup_supplier_id = str(row.get("backup_supplier_id", "")) or f"B{len(nodes) + 1}"
        component = str(row.get("component", "Component"))
        value_usd = float(row.get("value_usd", 0) or 0)
        criticality = float(row.get("criticality", 0.5) or 0.5)

        nodes.append(
            {
                "id": supplier_id,
                "shipment_id": shipment_id,
                "backup_supplier_id": backup_supplier_id,
                "name": component,
                "country": country,
                "lat": lat,
                "lng": lng,
                "component": component,
                "value_usd": int(value_usd),
                "criticality": criticality,
            }
        )
        arcs.append(
            {
                "id": f"{supplier_id}-arc",
                "supplier_id": supplier_id,
                "shipment_id": shipment_id,
                "backup_supplier_id": backup_supplier_id,
                "component": component,
                "country": country,
                "value_usd": int(value_usd),
                "criticality": criticality,
                "startLat": lat,
                "startLng": lng,
                "endLat": ASSEMBLY_PLANT["lat"],
                "endLng": ASSEMBLY_PLANT["lng"],
            }
        )

    return {
        "product": product,
        "assembly": ASSEMBLY_PLANT,
        "nodes": nodes,
        "arcs": arcs,
        "unresolved_countries": sorted(set(unresolved)),
        "total_value_usd": int(sum(n["value_usd"] for n in nodes)),
    }


def default_supply_chain(product: str = DEFAULT_PRODUCT) -> dict:
    stored_chain = get_supply_chain(product)
    if stored_chain is not None:
        ACTIVE_SUPPLY_CHAINS[product] = copy.deepcopy(stored_chain)
        return copy.deepcopy(stored_chain)

    if product in ACTIVE_SUPPLY_CHAINS:
        return copy.deepcopy(ACTIVE_SUPPLY_CHAINS[product])

    df = pd.read_csv(SUPPLIERS_CSV)
    chain = _build_from_dataframe(df, product)
    save_supply_chain(chain, source="bundled_seed")
    ACTIVE_SUPPLY_CHAINS[product] = copy.deepcopy(chain)
    return chain


def active_product_name() -> str:
    latest_product = get_latest_product()
    if latest_product:
        return latest_product
    return ACTIVE_PRODUCT


def parse_supply_chain_csv(content: bytes, product: str = DEFAULT_PRODUCT) -> dict:
    global ACTIVE_PRODUCT
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [c.strip().lower() for c in df.columns]
    chain = _build_from_dataframe(df, product)
    save_supply_chain(chain, source="csv_upload")
    ACTIVE_SUPPLY_CHAINS[product] = copy.deepcopy(chain)
    ACTIVE_PRODUCT = product
    return chain
