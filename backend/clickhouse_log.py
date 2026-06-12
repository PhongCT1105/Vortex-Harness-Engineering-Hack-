"""ClickHouse Event Log — see docs/API_CONTRACT.md §2."""

import time
from typing import Any

from clickhouse_store import get_events as get_clickhouse_events
from clickhouse_store import save_event

EVENTS: list[dict] = []


def log_event(kind: str, payload: Any, incident_id: str | None = None) -> None:
    row = {
        "ts": time.time(),
        "incident_id": incident_id or "",
        "kind": kind,
        "payload": payload,
    }
    EVENTS.append(row)
    save_event(row)


def read_events() -> list[dict]:
    return get_clickhouse_events() or EVENTS
