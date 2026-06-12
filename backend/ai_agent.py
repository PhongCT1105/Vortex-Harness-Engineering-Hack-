"""AI orchestration helpers.

These helpers are best-effort: use the configured LLM when available and return
structured fallbacks when the provider is unavailable. They never raise into the
pipeline.
"""

import json
from typing import Any

import httpx

from config import get_active_model, get_key
from supply_chain import DEFAULT_PRODUCT
from supply_chain_weather import get_supply_chain_weather, run_weather_tool, weather_tool_definitions


def _json_from_text(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _anthropic_json(prompt: str, max_tokens: int = 700) -> dict[str, Any] | None:
    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": get_key("ANTHROPIC_MODEL") or "claude-sonnet-4-5",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        return _json_from_text(resp.json()["content"][0]["text"])
    except Exception:
        return None


def _anthropic_tool_json(prompt: str, max_tokens: int = 1200) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        return None, []

    tool_calls = []
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    try:
        first = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": get_key("ANTHROPIC_MODEL") or "claude-sonnet-4-5",
                "max_tokens": max_tokens,
                "tools": weather_tool_definitions(),
                "messages": messages,
            },
            timeout=30,
        )
        first.raise_for_status()
        first_payload = first.json()
        content = first_payload.get("content", [])
        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        if not tool_uses:
            return _json_from_text(content[0]["text"]) if content and content[0].get("type") == "text" else None, []

        tool_results = []
        for block in tool_uses[:3]:
            name = block["name"]
            tool_input = block.get("input") or {}
            result = run_weather_tool(name, tool_input)
            compact_result = _compact_tool_result(result)
            tool_calls.append({"name": name, "input": tool_input, "result": compact_result})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": json.dumps(compact_result, default=str),
                }
            )

        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": tool_results})
        final = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": get_key("ANTHROPIC_MODEL") or "claude-sonnet-4-5",
                "max_tokens": max_tokens,
                "messages": messages,
            },
            timeout=30,
        )
        final.raise_for_status()
        final_content = final.json().get("content", [])
        text = next((block.get("text", "") for block in final_content if block.get("type") == "text"), "")
        return _json_from_text(text), tool_calls
    except Exception:
        return None, tool_calls


def _compact_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    if "countries" in result:
        return {
            "product": result.get("product"),
            "generated_at": result.get("generated_at"),
            "worst_risk_level": result.get("worst_risk_level"),
            "max_severity": result.get("max_severity"),
            "countries": [
                {
                    "country": row.get("country"),
                    "severity": row.get("severity"),
                    "risk_level": row.get("risk_level"),
                    "wind_kmh": row.get("wind_kmh"),
                    "precipitation_mm": row.get("precipitation_mm"),
                    "context": row.get("context"),
                }
                for row in result.get("countries", [])[:8]
            ],
            "routes": [
                {
                    "supplier_id": route.get("supplier_id"),
                    "component": route.get("component"),
                    "country": route.get("country"),
                    "max_severity": route.get("max_severity"),
                    "worst_risk_level": route.get("worst_risk_level"),
                    "worst_point": route.get("worst_point"),
                    "context": route.get("context"),
                }
                for route in result.get("routes", [])[:8]
            ],
        }
    if "routes" in result:
        return {
            "product": result.get("product"),
            "generated_at": result.get("generated_at"),
            "routes": [
                {
                    "supplier_id": route.get("supplier_id"),
                    "component": route.get("component"),
                    "country": route.get("country"),
                    "max_severity": route.get("max_severity"),
                    "worst_risk_level": route.get("worst_risk_level"),
                    "worst_point": route.get("worst_point"),
                    "context": route.get("context"),
                }
                for route in result.get("routes", [])[:8]
            ],
        }
    return result


def _deepseek_json(prompt: str, max_tokens: int = 700) -> dict[str, Any] | None:
    api_key = get_key("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    try:
        resp = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            json={
                "model": get_key("DEEPSEEK_MODEL") or "deepseek-chat",
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        return _json_from_text(resp.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def llm_json(prompt: str, max_tokens: int = 700) -> dict[str, Any] | None:
    providers = {
        "claude": _anthropic_json,
        "deepseek": _deepseek_json,
    }
    primary = get_active_model()
    fallback = "deepseek" if primary == "claude" else "claude"
    return providers[primary](prompt, max_tokens) or providers[fallback](prompt, max_tokens)


def orchestration_agent(
    event_text: str,
    weather: dict,
    impact: dict,
    actions: list[dict],
    product: str = DEFAULT_PRODUCT,
) -> dict:
    prompt = f"""
You are a supply-chain incident commander. Use the provided incident data and, when useful,
call the available weather tools to inspect the current uploaded supply chain and possible
supplier-to-assembly route weather. The route tools refresh every 4 hours unless explicitly
forced.
Return strict JSON with this exact shape:
{{
  "source": "claude|deepseek|rules",
  "executive_summary": "one sentence",
  "damaged_nodes": [
    {{"node": "supplier lane or component", "reason": "why it is damaged", "severity": "watch|elevated|critical"}}
  ],
  "priority_order": ["shipment ids in the order an operator should inspect"],
  "operator_questions": ["3 useful follow-up questions"],
  "route_weather_findings": ["short route-level weather findings"],
  "confidence": 0.0
}}

Product:
{product}

Trigger event:
{event_text}

Weather:
{json.dumps(weather, default=str)}

Impact:
{json.dumps(impact, default=str)}

Proposed actions:
{json.dumps(actions, default=str)}
"""
    tool_calls: list[dict[str, Any]] = []
    if get_active_model() == "claude":
        data, tool_calls = _anthropic_tool_json(prompt, max_tokens=1200)
        if data:
            data["source"] = "claude"
            data["tool_calls"] = tool_calls
            return data

    data = llm_json(prompt, max_tokens=900)
    if data:
        data["source"] = get_active_model()
        data["tool_calls"] = tool_calls
        return data

    shipments = impact.get("shipments", [])
    try:
        route_weather = get_supply_chain_weather(product)
        route_findings = [route["context"] for route in route_weather.get("routes", [])[:3]]
    except Exception:
        route_findings = []
    damaged = [
        {
            "node": f"{shipment['component']} / {shipment['country']}",
            "reason": f"Shipment {shipment['shipment_id']} risk score {shipment['risk_score']}",
            "severity": "critical" if shipment["risk_score"] >= 0.7 else "elevated",
        }
        for shipment in shipments[:4]
    ]
    return {
        "source": "rules",
        "executive_summary": (
            f"{weather['risk_level'].title()} weather risk affects "
            f"{impact['at_risk_shipments']} shipments across "
            f"{', '.join(weather['affected_countries'])}."
        ),
        "damaged_nodes": damaged,
        "priority_order": [shipment["shipment_id"] for shipment in shipments],
        "operator_questions": [
            "Which supplier lane is most damaged?",
            "Which route weather point is worst right now?",
            "Which actions require approval?",
        ],
        "route_weather_findings": route_findings,
        "tool_calls": [
            {
                "name": "get_supply_chain_weather_intelligence",
                "input": {"product": product, "force_refresh": False},
                "result": {"route_weather_findings": route_findings},
            }
        ],
        "confidence": 0.55,
    }
