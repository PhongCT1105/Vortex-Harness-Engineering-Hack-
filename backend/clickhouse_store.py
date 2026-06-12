"""ClickHouse persistence for StormOps runtime data.

ClickHouse is the primary store when configured. Callers still keep local
fallbacks so the hack demo can run without keys, but all upload, map, weather,
and audit data flows through this module first.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from config import get_key

_client = None
_schema_ready = False


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


def _json_loads(value: str | bytes | bytearray) -> Any:
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    return json.loads(value)


def get_client():
    global _client
    if _client is not None:
        return _client

    host = get_key("CLICKHOUSE_HOST")
    if not host:
        return None

    try:
        import clickhouse_connect

        _client = clickhouse_connect.get_client(
            host=host,
            port=int(get_key("CLICKHOUSE_PORT") or "8443"),
            username=get_key("CLICKHOUSE_USER") or "default",
            password=get_key("CLICKHOUSE_PASSWORD") or "",
            database=get_key("CLICKHOUSE_DATABASE") or "default",
        )
        ensure_schema()
        return _client
    except Exception:
        _client = None
        return None


def is_available() -> bool:
    return get_client() is not None


def ensure_schema() -> bool:
    global _schema_ready
    if _schema_ready and _client is not None:
        return True

    client = _client
    if client is None:
        return False

    try:
        client.command(
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                ts Float64,
                incident_id String,
                kind String,
                payload String
            ) ENGINE = MergeTree
            ORDER BY (ts, kind, incident_id)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_snapshots (
                uploaded_at Float64,
                product String,
                batch_id String,
                source String,
                payload String,
                unresolved_countries Array(String),
                total_value_usd UInt64
            ) ENGINE = MergeTree
            ORDER BY (product, uploaded_at, batch_id)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_nodes (
                uploaded_at Float64,
                product String,
                batch_id String,
                supplier_id String,
                shipment_id String,
                backup_supplier_id String,
                name String,
                country String,
                lat Float64,
                lng Float64,
                component String,
                value_usd Float64,
                criticality Float64
            ) ENGINE = MergeTree
            ORDER BY (product, batch_id, supplier_id)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_arcs (
                uploaded_at Float64,
                product String,
                batch_id String,
                arc_id String,
                supplier_id String,
                shipment_id String,
                backup_supplier_id String,
                component String,
                country String,
                value_usd Float64,
                criticality Float64,
                start_lat Float64,
                start_lng Float64,
                end_lat Float64,
                end_lng Float64
            ) ENGINE = MergeTree
            ORDER BY (product, batch_id, arc_id)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_weather_snapshots (
                generated_ts Float64,
                expires_ts Float64,
                product String,
                snapshot_id String,
                source String,
                worst_risk_level String,
                max_severity Float64,
                payload String
            ) ENGINE = MergeTree
            ORDER BY (product, generated_ts, snapshot_id)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_weather_countries (
                generated_ts Float64,
                product String,
                snapshot_id String,
                country String,
                lat Float64,
                lng Float64,
                supplier_count UInt64,
                components Array(String),
                value_usd Float64,
                avg_criticality Float64,
                wind_kmh Float64,
                precipitation_mm Float64,
                temperature_c Float64,
                severity Float64,
                risk_level String,
                source String,
                payload String
            ) ENGINE = MergeTree
            ORDER BY (product, generated_ts, country)
            """
        )
        client.command(
            """
            CREATE TABLE IF NOT EXISTS supply_chain_weather_routes (
                generated_ts Float64,
                product String,
                snapshot_id String,
                supplier_id String,
                component String,
                country String,
                value_usd Float64,
                criticality Float64,
                max_severity Float64,
                worst_risk_level String,
                worst_point String,
                payload String
            ) ENGINE = MergeTree
            ORDER BY (product, generated_ts, supplier_id)
            """
        )
        _schema_ready = True
        return True
    except Exception:
        return False


def reset_schema() -> bool:
    """Drop StormOps tables and recreate them.

    This intentionally removes old ClickHouse data for this project only.
    """
    global _schema_ready
    client = get_client()
    if client is None:
        return False

    for table in (
        "supply_chain_weather_routes",
        "supply_chain_weather_countries",
        "supply_chain_weather_snapshots",
        "supply_chain_arcs",
        "supply_chain_nodes",
        "supply_chain_snapshots",
        "agent_events",
    ):
        client.command(f"DROP TABLE IF EXISTS {table}")

    _schema_ready = False
    return ensure_schema()


def save_event(row: dict[str, Any]) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.insert(
            "agent_events",
            [[row["ts"], row.get("incident_id") or "", row["kind"], _json_dumps(row["payload"])]],
            column_names=["ts", "incident_id", "kind", "payload"],
        )
        return True
    except Exception:
        return False


def get_events(limit: int = 500) -> list[dict[str, Any]] | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.query(
            """
            SELECT ts, incident_id, kind, payload
            FROM agent_events
            ORDER BY ts ASC
            LIMIT %(limit)s
            """,
            parameters={"limit": limit},
        )
        return [
            {
                "ts": float(ts),
                "incident_id": incident_id,
                "kind": kind,
                "payload": _json_loads(payload),
            }
            for ts, incident_id, kind, payload in result.result_rows
        ]
    except Exception:
        return None


def get_recent_events(limit: int = 50, incident_id: str | None = None) -> list[dict[str, Any]] | None:
    client = get_client()
    if client is None:
        return None
    incident_filter = "WHERE incident_id = %(incident_id)s" if incident_id else ""
    try:
        result = client.query(
            f"""
            SELECT ts, incident_id, kind, payload
            FROM agent_events
            {incident_filter}
            ORDER BY ts DESC
            LIMIT %(limit)s
            """,
            parameters={"limit": limit, "incident_id": incident_id or ""},
        )
        rows = [
            {
                "ts": float(ts),
                "incident_id": incident,
                "kind": kind,
                "payload": _json_loads(payload),
            }
            for ts, incident, kind, payload in result.result_rows
        ]
        rows.reverse()
        return rows
    except Exception:
        return None


def save_supply_chain(chain: dict[str, Any], source: str = "upload") -> bool:
    client = get_client()
    if client is None:
        return False

    uploaded_at = time.time()
    product = str(chain["product"])
    batch_id = uuid.uuid4().hex
    nodes = chain.get("nodes", [])
    arcs = chain.get("arcs", [])

    try:
        client.insert(
            "supply_chain_snapshots",
            [
                [
                    uploaded_at,
                    product,
                    batch_id,
                    source,
                    _json_dumps(chain),
                    list(chain.get("unresolved_countries") or []),
                    int(chain.get("total_value_usd") or 0),
                ]
            ],
            column_names=[
                "uploaded_at",
                "product",
                "batch_id",
                "source",
                "payload",
                "unresolved_countries",
                "total_value_usd",
            ],
        )
        if nodes:
            client.insert(
                "supply_chain_nodes",
                [
                    [
                        uploaded_at,
                        product,
                        batch_id,
                        str(node.get("id") or ""),
                        str(node.get("shipment_id") or ""),
                        str(node.get("backup_supplier_id") or ""),
                        str(node.get("name") or ""),
                        str(node.get("country") or ""),
                        float(node.get("lat") or 0),
                        float(node.get("lng") or 0),
                        str(node.get("component") or ""),
                        float(node.get("value_usd") or 0),
                        float(node.get("criticality") or 0),
                    ]
                    for node in nodes
                ],
                column_names=[
                    "uploaded_at",
                    "product",
                    "batch_id",
                    "supplier_id",
                    "shipment_id",
                    "backup_supplier_id",
                    "name",
                    "country",
                    "lat",
                    "lng",
                    "component",
                    "value_usd",
                    "criticality",
                ],
            )
        if arcs:
            client.insert(
                "supply_chain_arcs",
                [
                    [
                        uploaded_at,
                        product,
                        batch_id,
                        str(arc.get("id") or ""),
                        str(arc.get("supplier_id") or ""),
                        str(arc.get("shipment_id") or ""),
                        str(arc.get("backup_supplier_id") or ""),
                        str(arc.get("component") or ""),
                        str(arc.get("country") or ""),
                        float(arc.get("value_usd") or 0),
                        float(arc.get("criticality") or 0),
                        float(arc.get("startLat") or 0),
                        float(arc.get("startLng") or 0),
                        float(arc.get("endLat") or 0),
                        float(arc.get("endLng") or 0),
                    ]
                    for arc in arcs
                ],
                column_names=[
                    "uploaded_at",
                    "product",
                    "batch_id",
                    "arc_id",
                    "supplier_id",
                    "shipment_id",
                    "backup_supplier_id",
                    "component",
                    "country",
                    "value_usd",
                    "criticality",
                    "start_lat",
                    "start_lng",
                    "end_lat",
                    "end_lng",
                ],
            )
        return True
    except Exception:
        return False


def get_supply_chain(product: str) -> dict[str, Any] | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.query(
            """
            SELECT payload
            FROM supply_chain_snapshots
            WHERE product = %(product)s
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            parameters={"product": product},
        )
        if not result.result_rows:
            return None
        return _json_loads(result.result_rows[0][0])
    except Exception:
        return None


def get_latest_product() -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.query(
            """
            SELECT product
            FROM supply_chain_snapshots
            ORDER BY uploaded_at DESC
            LIMIT 1
            """
        )
        if not result.result_rows:
            return None
        return str(result.result_rows[0][0])
    except Exception:
        return None


def get_supply_chain_summary(product: str) -> dict[str, Any] | None:
    client = get_client()
    if client is None:
        return None
    try:
        snapshot = client.query(
            """
            SELECT uploaded_at, batch_id, source, unresolved_countries, total_value_usd
            FROM supply_chain_snapshots
            WHERE product = %(product)s
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            parameters={"product": product},
        )
        if not snapshot.result_rows:
            return None
        uploaded_at, batch_id, source, unresolved, total_value = snapshot.result_rows[0]
        countries = client.query(
            """
            SELECT country, count() AS suppliers, sum(value_usd) AS value_usd, avg(criticality) AS avg_criticality
            FROM supply_chain_nodes
            WHERE product = %(product)s AND batch_id = %(batch_id)s
            GROUP BY country
            ORDER BY value_usd DESC
            """,
            parameters={"product": product, "batch_id": batch_id},
        )
        top_nodes = client.query(
            """
            SELECT supplier_id, shipment_id, component, country, value_usd, criticality
            FROM supply_chain_nodes
            WHERE product = %(product)s AND batch_id = %(batch_id)s
            ORDER BY criticality DESC, value_usd DESC
            LIMIT 10
            """,
            parameters={"product": product, "batch_id": batch_id},
        )
        return {
            "product": product,
            "uploaded_at": float(uploaded_at),
            "batch_id": batch_id,
            "source": source,
            "total_value_usd": int(total_value),
            "unresolved_countries": list(unresolved),
            "countries": [
                {
                    "country": country,
                    "suppliers": int(suppliers),
                    "value_usd": int(value),
                    "avg_criticality": round(float(avg_criticality), 2),
                }
                for country, suppliers, value, avg_criticality in countries.result_rows
            ],
            "top_suppliers": [
                {
                    "supplier_id": supplier_id,
                    "shipment_id": shipment_id,
                    "component": component,
                    "country": country,
                    "value_usd": int(value_usd),
                    "criticality": float(criticality),
                }
                for supplier_id, shipment_id, component, country, value_usd, criticality in top_nodes.result_rows
            ],
        }
    except Exception:
        return None


def save_weather_snapshot(payload: dict[str, Any]) -> bool:
    client = get_client()
    if client is None:
        return False

    generated_at = _parse_iso_ts(payload["generated_at"])
    expires_at = _parse_iso_ts(payload["expires_at"])
    product = str(payload["product"])
    snapshot_id = uuid.uuid4().hex
    countries = payload.get("countries", [])
    routes = payload.get("routes", [])

    try:
        client.insert(
            "supply_chain_weather_snapshots",
            [
                [
                    generated_at,
                    expires_at,
                    product,
                    snapshot_id,
                    str(payload.get("source") or ""),
                    str(payload.get("worst_risk_level") or ""),
                    float(payload.get("max_severity") or 0),
                    _json_dumps(payload),
                ]
            ],
            column_names=[
                "generated_ts",
                "expires_ts",
                "product",
                "snapshot_id",
                "source",
                "worst_risk_level",
                "max_severity",
                "payload",
            ],
        )
        if countries:
            client.insert(
                "supply_chain_weather_countries",
                [
                    [
                        generated_at,
                        product,
                        snapshot_id,
                        str(country.get("country") or ""),
                        float(country.get("lat") or 0),
                        float(country.get("lng") or 0),
                        int(country.get("supplier_count") or 0),
                        [str(component) for component in country.get("components", [])],
                        float(country.get("value_usd") or 0),
                        float(country.get("avg_criticality") or 0),
                        float(country.get("wind_kmh") or 0),
                        float(country.get("precipitation_mm") or 0),
                        float(country.get("temperature_c") or 0),
                        float(country.get("severity") or 0),
                        str(country.get("risk_level") or ""),
                        str(country.get("source") or ""),
                        _json_dumps(country),
                    ]
                    for country in countries
                ],
                column_names=[
                    "generated_ts",
                    "product",
                    "snapshot_id",
                    "country",
                    "lat",
                    "lng",
                    "supplier_count",
                    "components",
                    "value_usd",
                    "avg_criticality",
                    "wind_kmh",
                    "precipitation_mm",
                    "temperature_c",
                    "severity",
                    "risk_level",
                    "source",
                    "payload",
                ],
            )
        if routes:
            client.insert(
                "supply_chain_weather_routes",
                [
                    [
                        generated_at,
                        product,
                        snapshot_id,
                        str(route.get("supplier_id") or ""),
                        str(route.get("component") or ""),
                        str(route.get("country") or ""),
                        float(route.get("value_usd") or 0),
                        float(route.get("criticality") or 0),
                        float(route.get("max_severity") or 0),
                        str(route.get("worst_risk_level") or ""),
                        str(route.get("worst_point") or ""),
                        _json_dumps(route),
                    ]
                    for route in routes
                ],
                column_names=[
                    "generated_ts",
                    "product",
                    "snapshot_id",
                    "supplier_id",
                    "component",
                    "country",
                    "value_usd",
                    "criticality",
                    "max_severity",
                    "worst_risk_level",
                    "worst_point",
                    "payload",
                ],
            )
        return True
    except Exception:
        return False


def get_weather_snapshot(product: str, require_fresh: bool = True) -> dict[str, Any] | None:
    client = get_client()
    if client is None:
        return None
    freshness_filter = "AND expires_ts > %(now)s" if require_fresh else ""
    try:
        result = client.query(
            f"""
            SELECT payload
            FROM supply_chain_weather_snapshots
            WHERE product = %(product)s
            {freshness_filter}
            ORDER BY generated_ts DESC
            LIMIT 1
            """,
            parameters={"product": product, "now": time.time()},
        )
        if not result.result_rows:
            return None
        return _json_loads(result.result_rows[0][0])
    except Exception:
        return None


def _parse_iso_ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
