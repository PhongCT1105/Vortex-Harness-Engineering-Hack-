"""ClickHouse Event Log — see docs/API_CONTRACT.md §2.

EVENTS (in-memory) is always written to and is what GET /events reads.
ClickHouse insert is best-effort and additive.
"""

import time
from typing import Any

from config import get_key

EVENTS: list[dict] = []

_client = None


def _get_client():
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
        _client.command(
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                ts Float64,
                incident_id String,
                kind String,
                payload String
            ) ENGINE = MergeTree ORDER BY ts
            """
        )
        return _client
    except Exception:
        _client = None
        return None


def log_event(kind: str, payload: Any, incident_id: str | None = None) -> None:
    row = {
        "ts": time.time(),
        "incident_id": incident_id or "",
        "kind": kind,
        "payload": payload,
    }
    EVENTS.append(row)

    client = _get_client()
    if client is None:
        return

    try:
        import json

        client.insert(
            "agent_events",
            [[row["ts"], row["incident_id"], row["kind"], json.dumps(payload, default=str)]],
            column_names=["ts", "incident_id", "kind", "payload"],
        )
    except Exception:
        pass
