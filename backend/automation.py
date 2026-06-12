"""Real weather-driven StormOps automation.

This path is driven by the current supply-chain map and live weather snapshots,
not by a hand-entered scenario. It builds a persisted context layer, asks the
reasoning model to analyze that context, and dispatches the report downstream.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from ai_agent import supply_chain_report_agent
from clickhouse_log import log_event
from clickhouse_store import (
    get_recent_events,
    get_supply_chain_summary,
    get_weather_snapshot,
    save_context_snapshot,
)
from comms import dispatch_report
from supply_chain import DEFAULT_PRODUCT, default_supply_chain
from supply_chain_weather import get_supply_chain_weather


def _compact_weather(weather: dict[str, Any]) -> dict[str, Any]:
    return {
        "product": weather.get("product"),
        "generated_at": weather.get("generated_at"),
        "expires_at": weather.get("expires_at"),
        "worst_risk_level": weather.get("worst_risk_level"),
        "max_severity": weather.get("max_severity"),
        "countries": [
            {
                "country": country.get("country"),
                "risk_level": country.get("risk_level"),
                "severity": country.get("severity"),
                "wind_kmh": country.get("wind_kmh"),
                "precipitation_mm": country.get("precipitation_mm"),
                "context": country.get("context"),
            }
            for country in weather.get("countries", [])[:10]
        ],
        "routes": [
            {
                "supplier_id": route.get("supplier_id"),
                "component": route.get("component"),
                "country": route.get("country"),
                "max_severity": route.get("max_severity"),
                "worst_risk_level": route.get("worst_risk_level"),
                "context": route.get("context"),
            }
            for route in weather.get("routes", [])[:10]
        ],
    }


def _event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        kind = str(event.get("kind") or "")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def build_context_layer(
    automation_id: str,
    product: str,
    trigger_source: str,
    weather_source: str,
    chain: dict[str, Any],
    weather_snapshot: dict[str, Any],
) -> dict[str, Any]:
    recent_events = get_recent_events(50) or []
    summary = get_supply_chain_summary(product)
    context = {
        "created_ts": time.time(),
        "automation_id": automation_id,
        "product": product,
        "trigger_source": trigger_source,
        "weather_source": weather_source,
        "worst_risk_level": weather_snapshot.get("worst_risk_level"),
        "max_severity": weather_snapshot.get("max_severity"),
        "supply_chain": summary
        or {
            "product": product,
            "total_value_usd": chain.get("total_value_usd"),
            "supplier_count": len(chain.get("nodes", [])),
            "route_count": len(chain.get("arcs", [])),
        },
        "weather": _compact_weather(weather_snapshot),
        "audit": {
            "recent_event_count": len(recent_events),
            "event_counts": _event_counts(recent_events),
            "recent_events": [
                {
                    "ts": event.get("ts"),
                    "incident_id": event.get("incident_id"),
                    "kind": event.get("kind"),
                }
                for event in recent_events[-20:]
            ],
        },
    }
    save_context_snapshot(context)
    return context


def run_real_weather_pipeline(
    product: str = DEFAULT_PRODUCT,
    force_refresh: bool = False,
    trigger_source: str = "manual",
) -> dict[str, Any]:
    automation_id = uuid.uuid4().hex[:8]
    log_event(
        "automation_started",
        {
            "automation_id": automation_id,
            "product": product,
            "force_refresh": force_refresh,
            "trigger_source": trigger_source,
        },
        automation_id,
    )

    chain = default_supply_chain(product)
    fresh_snapshot = None if force_refresh else get_weather_snapshot(product, require_fresh=True)
    if fresh_snapshot is not None:
        weather_snapshot = fresh_snapshot
        weather_source = "clickhouse_cached"
        log_event(
            "weather_snapshot_reused",
            {
                "automation_id": automation_id,
                "product": product,
                "generated_at": weather_snapshot.get("generated_at"),
                "expires_at": weather_snapshot.get("expires_at"),
            },
            automation_id,
        )
    else:
        weather_snapshot = get_supply_chain_weather(product, force_refresh=True)
        weather_source = "refreshed"
        log_event(
            "weather_snapshot_refreshed",
            {
                "automation_id": automation_id,
                "product": product,
                "generated_at": weather_snapshot.get("generated_at"),
                "expires_at": weather_snapshot.get("expires_at"),
                "worst_risk_level": weather_snapshot.get("worst_risk_level"),
                "max_severity": weather_snapshot.get("max_severity"),
            },
            automation_id,
        )

    context = build_context_layer(
        automation_id,
        product,
        trigger_source,
        weather_source,
        chain,
        weather_snapshot,
    )
    log_event("automation_context_created", context, automation_id)

    report = supply_chain_report_agent(product, chain, weather_snapshot, automation_id)
    report["context_id"] = automation_id
    log_event("automation_report_generated", report, automation_id)

    dispatch = dispatch_report(report)
    log_event("automation_report_dispatched", dispatch, automation_id)

    return {
        "automation_id": automation_id,
        "product": product,
        "trigger_source": trigger_source,
        "weather_source": weather_source,
        "weather_generated_at": weather_snapshot.get("generated_at"),
        "context": context,
        "report": report,
        "dispatch": dispatch,
    }
