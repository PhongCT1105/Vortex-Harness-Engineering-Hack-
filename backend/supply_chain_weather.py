"""Supply-chain weather intelligence.

Builds a cached weather-risk view for every country in the current supply chain.
Open-Meteo provides no-key numeric weather, and DuckDuckGo HTML search provides
free contextual snippets. Both paths fail closed into structured fallback rows.
"""

from __future__ import annotations

import asyncio
import html
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import httpx

from clickhouse_store import get_weather_snapshot, save_weather_snapshot
from config import get_key
from supply_chain import ASSEMBLY_PLANT, DEFAULT_PRODUCT, default_supply_chain

REFRESH_SECONDS = int(float(os.getenv("SUPPLY_CHAIN_WEATHER_REFRESH_HOURS", "4")) * 3600)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DUCKDUCKGO_URL = "https://duckduckgo.com/html/"
WEATHERAPI_URL = "https://api.weatherapi.com/v1/current.json"
WTTR_URL = "https://wttr.in/{lat},{lng}"

_CACHE: dict[str, Any] | None = None
_CACHE_TS = 0.0
_LOCK = threading.Lock()

WEATHER_CODE_CONTEXT = {
    0: "Clear conditions. Weather is unlikely to disrupt normal supplier operations.",
    1: "Mainly clear conditions. Monitor exposed transport lanes, but disruption risk is low.",
    2: "Partly cloudy conditions. Operational weather risk is limited.",
    3: "Overcast conditions. Watch visibility-sensitive logistics, but risk is generally low.",
    45: "Fog is present. Road and port handling may slow because of reduced visibility.",
    48: "Depositing fog is present. Localized road delays are possible.",
    51: "Light drizzle. Minor loading and local road delays are possible.",
    53: "Moderate drizzle. Exposed yard work and short-haul transport may slow.",
    55: "Dense drizzle. Expect localized handling delays and slower road movement.",
    61: "Light rain. Road transport can continue with moderate caution.",
    63: "Moderate rain. Supplier pickup windows and highway movements may slip.",
    65: "Heavy rain. Flooding and road disruption become credible logistics risks.",
    71: "Light snow. Road movement may slow, especially around supplier yards.",
    73: "Moderate snow. Trucking and last-mile supplier pickup reliability are at risk.",
    75: "Heavy snow. Expect meaningful disruption to road and warehouse operations.",
    80: "Rain showers. Short disruptions are possible around exposed handoff points.",
    81: "Moderate rain showers. Pickup windows and loading operations may be delayed.",
    82: "Violent rain showers. High risk of localized flooding and transport disruption.",
    95: "Thunderstorm conditions. Outdoor handling, road transport, and power reliability are exposed.",
    96: "Thunderstorms with hail. Supplier facilities and transport routes face elevated disruption risk.",
    99: "Severe thunderstorms with hail. Treat exposed shipments as high-risk until conditions improve.",
}


def _risk_level(severity: float) -> str:
    if severity >= 0.66:
        return "severe"
    if severity >= 0.4:
        return "high"
    if severity >= 0.2:
        return "watch"
    return "normal"


def _severity(wind_kmh: float, precipitation_mm: float, temperature_c: float, weather_code: int | None) -> float:
    score = min(1.0, (wind_kmh / 120) * 0.45 + (precipitation_mm / 80) * 0.4)
    if temperature_c <= -5 or temperature_c >= 38:
        score = min(1.0, score + 0.12)
    if weather_code in {65, 75, 82, 95, 96, 99}:
        score = min(1.0, score + 0.12)
    return round(score, 2)


def _country_summary(row: dict[str, Any]) -> str:
    code_context = WEATHER_CODE_CONTEXT.get(
        row.get("weather_code"),
        "Weather data is available, but the exact condition code is not classified locally.",
    )
    level = row["risk_level"]
    return (
        f"{row['country']} is at {level} supply-chain weather risk: "
        f"{row['wind_kmh']} km/h wind, {row['precipitation_mm']} mm precipitation, "
        f"{row['temperature_c']} C. {code_context}"
    )


def _fetch_open_meteo(lat: float, lng: float) -> dict[str, Any]:
    resp = httpx.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "precipitation_sum,wind_speed_10m_max",
            "forecast_days": 1,
            "timezone": "UTC",
        },
        timeout=6,
    )
    resp.raise_for_status()
    data = resp.json()
    current = data.get("current", {})
    daily = data.get("daily", {})
    daily_precip = (daily.get("precipitation_sum") or [None])[0]
    daily_wind = (daily.get("wind_speed_10m_max") or [None])[0]
    return {
        "wind_kmh": float(daily_wind if daily_wind is not None else current.get("wind_speed_10m", 0)),
        "precipitation_mm": float(
            daily_precip if daily_precip is not None else current.get("precipitation", 0)
        ),
        "temperature_c": float(current.get("temperature_2m", 0)),
        "weather_code": int(current["weather_code"]) if current.get("weather_code") is not None else None,
    }


def _fetch_weatherapi(lat: float, lng: float) -> dict[str, Any] | None:
    api_key = get_key("WEATHERAPI_KEY")
    if not api_key:
        return None
    resp = httpx.get(
        WEATHERAPI_URL,
        params={"key": api_key, "q": f"{lat},{lng}", "aqi": "no"},
        timeout=6,
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    return {
        "wind_kmh": float(current.get("wind_kph", 0)),
        "precipitation_mm": float(current.get("precip_mm", 0)),
        "temperature_c": float(current.get("temp_c", 0)),
        "weather_code": None,
        "condition": str(current.get("condition", {}).get("text", "")),
    }


def _fetch_wttr(lat: float, lng: float) -> dict[str, Any]:
    resp = httpx.get(
        WTTR_URL.format(lat=lat, lng=lng),
        params={"format": "j1"},
        headers={"User-Agent": "StormOps/1.0"},
        timeout=6,
    )
    resp.raise_for_status()
    current = resp.json()["current_condition"][0]
    return {
        "wind_kmh": float(current.get("windspeedKmph", 0)),
        "precipitation_mm": float(current.get("precipMM", 0)),
        "temperature_c": float(current.get("temp_C", 0)),
        "weather_code": None,
        "condition": str((current.get("weatherDesc") or [{}])[0].get("value", "")),
    }


def _provider_readings(lat: float, lng: float) -> list[dict[str, Any]]:
    readings = []
    providers = [
        ("open-meteo", lambda: _fetch_open_meteo(lat, lng)),
        ("weatherapi", lambda: _fetch_weatherapi(lat, lng)),
        ("wttr", lambda: _fetch_wttr(lat, lng)),
    ]
    for source, fetcher in providers:
        try:
            data = fetcher()
            if data is not None:
                readings.append({"source": source, **data})
        except Exception:
            continue
    return readings


def _aggregate_readings(readings: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if not readings:
        return (
            "rules",
            {
                "wind_kmh": 20.0,
                "precipitation_mm": 0.0,
                "temperature_c": 18.0,
                "weather_code": None,
                "condition": "Provider data unavailable",
            },
        )
    return (
        "+".join(reading["source"] for reading in readings),
        {
            "wind_kmh": max(float(reading["wind_kmh"]) for reading in readings),
            "precipitation_mm": max(float(reading["precipitation_mm"]) for reading in readings),
            "temperature_c": sum(float(reading["temperature_c"]) for reading in readings) / len(readings),
            "weather_code": next((reading.get("weather_code") for reading in readings if reading.get("weather_code") is not None), None),
            "condition": "; ".join(
                f"{reading['source']}: {reading.get('condition')}"
                for reading in readings
                if reading.get("condition")
            ),
        },
    )


def _extract_search_results(markup: str, limit: int = 3) -> list[dict[str, str]]:
    results = []
    blocks = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', markup, re.S)
    snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', markup, re.S)
    for index, (url, title) in enumerate(blocks[:limit]):
        clean_title = re.sub("<.*?>", "", title)
        clean_snippet = re.sub("<.*?>", "", snippets[index] if index < len(snippets) else "")
        results.append(
            {
                "title": html.unescape(clean_title).strip(),
                "url": html.unescape(url).strip(),
                "snippet": html.unescape(clean_snippet).strip(),
            }
        )
    return [result for result in results if result["title"]]


def _search_context(country: str, risk_level: str) -> dict[str, Any]:
    query = f"{country} weather disruption logistics supply chain {datetime.now(timezone.utc).year}"
    try:
        resp = httpx.get(
            DUCKDUCKGO_URL,
            params={"q": query},
            headers={"User-Agent": "StormOps/1.0"},
            timeout=6,
        )
        resp.raise_for_status()
        results = _extract_search_results(resp.text)
        if results:
            return {
                "source": "duckduckgo",
                "query": query,
                "summary": f"Search context found {len(results)} recent result(s) for {country} weather and logistics disruption.",
                "results": results,
            }
    except Exception:
        pass

    return {
        "source": "rules",
        "query": query,
        "summary": f"No live search context was available. Use the numeric {risk_level} risk score as the current operating signal.",
        "results": [],
    }


def _weather_at_point(
    label: str,
    lat: float,
    lng: float,
    search_name: str,
    suppliers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider_readings = _provider_readings(lat, lng)
    source, numeric = _aggregate_readings(provider_readings)

    severity = _severity(
        numeric["wind_kmh"],
        numeric["precipitation_mm"],
        numeric["temperature_c"],
        numeric["weather_code"],
    )
    risk_level = _risk_level(severity)
    row = {
        "label": label,
        "country": search_name,
        "lat": lat,
        "lng": lng,
        "supplier_count": len(suppliers or []),
        "components": sorted({supplier["component"] for supplier in suppliers or []}),
        "value_usd": int(sum(supplier["value_usd"] for supplier in suppliers or [])),
        "avg_criticality": round(mean([supplier["criticality"] for supplier in suppliers]), 2) if suppliers else 0,
        "wind_kmh": round(numeric["wind_kmh"], 1),
        "precipitation_mm": round(numeric["precipitation_mm"], 1),
        "temperature_c": round(numeric["temperature_c"], 1),
        "weather_code": numeric["weather_code"],
        "condition": numeric.get("condition") or "",
        "severity": severity,
        "risk_level": risk_level,
        "source": source,
        "provider_readings": [
            {
                "source": reading["source"],
                "wind_kmh": round(float(reading["wind_kmh"]), 1),
                "precipitation_mm": round(float(reading["precipitation_mm"]), 1),
                "temperature_c": round(float(reading["temperature_c"]), 1),
                "condition": reading.get("condition") or "",
            }
            for reading in provider_readings
        ],
    }
    row["context"] = _country_summary(row)
    row["search"] = (
        _search_context(search_name, risk_level)
        if risk_level != "normal"
        else {
            "source": "rules",
            "query": "",
            "summary": "Current numeric weather is normal; no live disruption search was needed.",
            "results": [],
        }
    )
    return row


def _country_weather(country: str, lat: float, lng: float, suppliers: list[dict[str, Any]]) -> dict[str, Any]:
    return _weather_at_point(country, lat, lng, country, suppliers)


def _route_sample_points(arc: dict[str, Any], assembly: dict[str, Any]) -> list[dict[str, Any]]:
    start_lat = float(arc["startLat"])
    start_lng = float(arc["startLng"])
    end_lat = float(arc["endLat"])
    end_lng = float(arc["endLng"])
    country = arc["country"]
    component = arc["component"]
    return [
        {
            "kind": "origin",
            "label": f"{component} origin - {country}",
            "search_name": country,
            "lat": start_lat,
            "lng": start_lng,
        },
        {
            "kind": "route_midpoint",
            "label": f"{component} route midpoint",
            "search_name": f"{country} to {assembly['city']} logistics corridor",
            "lat": round((start_lat + end_lat) / 2, 4),
            "lng": round((start_lng + end_lng) / 2, 4),
        },
        {
            "kind": "assembly",
            "label": f"{assembly['city']} assembly inbound",
            "search_name": f"{assembly['city']} {assembly['country']}",
            "lat": end_lat,
            "lng": end_lng,
        },
    ]


def _route_weather(chain: dict[str, Any]) -> list[dict[str, Any]]:
    routes = []
    nodes_by_id = {node["id"]: node for node in chain["nodes"]}
    for arc in chain["arcs"]:
        supplier = nodes_by_id.get(arc["supplier_id"])
        if not supplier:
            continue
        points = []
        for point in _route_sample_points(arc, chain["assembly"]):
            weather = _weather_at_point(
                point["label"],
                point["lat"],
                point["lng"],
                point["search_name"],
                [supplier] if point["kind"] == "origin" else [],
            )
            points.append({**point, "weather": weather})
        worst = max(points, key=lambda item: item["weather"]["severity"])
        routes.append(
            {
                "supplier_id": arc["supplier_id"],
                "component": arc["component"],
                "country": arc["country"],
                "value_usd": arc["value_usd"],
                "criticality": arc["criticality"],
                "destination": {
                    "name": chain["assembly"]["name"],
                    "city": chain["assembly"]["city"],
                    "country": chain["assembly"]["country"],
                },
                "points": points,
                "max_severity": worst["weather"]["severity"],
                "worst_risk_level": worst["weather"]["risk_level"],
                "worst_point": worst["label"],
                "context": (
                    f"{arc['component']} from {arc['country']} to {chain['assembly']['city']} "
                    f"has {worst['weather']['risk_level']} route weather risk at {worst['label']} "
                    f"(severity {worst['weather']['severity']})."
                ),
            }
        )
    return sorted(routes, key=lambda route: (route["max_severity"], route["value_usd"]), reverse=True)


def _supply_chain_countries(product: str) -> list[dict[str, Any]]:
    chain = default_supply_chain(product)
    countries: dict[str, dict[str, Any]] = {}
    for node in chain["nodes"]:
        country = node["country"]
        countries.setdefault(
            country,
            {"country": country, "lat": node["lat"], "lng": node["lng"], "suppliers": []},
        )
        countries[country]["suppliers"].append(node)

    assembly_country = ASSEMBLY_PLANT["country"]
    countries.setdefault(
        assembly_country,
        {
            "country": assembly_country,
            "lat": ASSEMBLY_PLANT["lat"],
            "lng": ASSEMBLY_PLANT["lng"],
            "suppliers": [],
        },
    )

    return sorted(countries.values(), key=lambda item: item["country"])


def refresh_supply_chain_weather(product: str = DEFAULT_PRODUCT) -> dict[str, Any]:
    chain = default_supply_chain(product)
    countries = _supply_chain_countries(product)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(countries)))) as pool:
        rows = list(
            pool.map(
                lambda item: _country_weather(
                    item["country"],
                    item["lat"],
                    item["lng"],
                    item["suppliers"],
                ),
                countries,
            )
        )
    rows.sort(key=lambda row: (row["severity"], row["value_usd"], row["avg_criticality"]), reverse=True)
    routes = _route_weather(chain)
    max_country = rows[0]["severity"] if rows else 0
    max_route = routes[0]["max_severity"] if routes else 0
    worst_level = routes[0]["worst_risk_level"] if routes and max_route >= max_country else rows[0]["risk_level"] if rows else "normal"

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "product": product,
        "assembly": chain["assembly"],
        "generated_at": generated_at,
        "expires_at": datetime.fromtimestamp(time.time() + REFRESH_SECONDS, timezone.utc).isoformat(),
        "refresh_seconds": REFRESH_SECONDS,
        "source": "open-meteo+weatherapi+wttr+duckduckgo",
        "worst_risk_level": worst_level,
        "max_severity": max(max_country, max_route),
        "countries": rows,
        "routes": routes,
    }

    global _CACHE, _CACHE_TS
    with _LOCK:
        _CACHE = payload
        _CACHE_TS = time.time()
    save_weather_snapshot(payload)
    return payload


def get_supply_chain_weather(product: str = DEFAULT_PRODUCT, force_refresh: bool = False) -> dict[str, Any]:
    global _CACHE, _CACHE_TS
    with _LOCK:
        cache = _CACHE
        age = time.time() - _CACHE_TS
    if not force_refresh and cache is not None and age < REFRESH_SECONDS and cache.get("product") == product:
        return cache
    if not force_refresh:
        stored = get_weather_snapshot(product, require_fresh=True)
        if stored is not None:
            with _LOCK:
                _CACHE = stored
                _CACHE_TS = time.time()
            return stored
    return refresh_supply_chain_weather(product)


def invalidate_supply_chain_weather(product: str = DEFAULT_PRODUCT) -> None:
    global _CACHE, _CACHE_TS
    with _LOCK:
        if _CACHE is not None and _CACHE.get("product") == product:
            _CACHE = None
            _CACHE_TS = 0.0


def get_route_weather(product: str = DEFAULT_PRODUCT, supplier_id: str | None = None) -> dict[str, Any]:
    data = get_supply_chain_weather(product)
    routes = data.get("routes", [])
    if supplier_id:
        routes = [route for route in routes if route.get("supplier_id") == supplier_id]
    return {
        "product": data["product"],
        "generated_at": data["generated_at"],
        "refresh_seconds": data["refresh_seconds"],
        "routes": routes,
    }


def weather_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_supply_chain_weather_intelligence",
            "description": (
                "Fetch cached 4-hour supply-chain weather intelligence, including supplier "
                "countries, route sample points, provider readings, and disruption context."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product name to inspect."},
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Whether to bypass the 4-hour cache and fetch fresh provider data.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "lookup_route_weather",
            "description": (
                "Fetch route weather for all supplier-to-assembly lanes or one supplier lane. "
                "Use this when analyzing possible weather on the path, not just at the supplier country."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product name to inspect."},
                    "supplier_id": {
                        "type": "string",
                        "description": "Optional supplier id, for example S1. Omit to return all lanes.",
                    },
                },
                "required": [],
            },
        },
    ]


def run_weather_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    product = str(tool_input.get("product") or DEFAULT_PRODUCT)
    if name == "get_supply_chain_weather_intelligence":
        return get_supply_chain_weather(product, bool(tool_input.get("force_refresh", False)))
    if name == "lookup_route_weather":
        supplier_id = tool_input.get("supplier_id")
        return get_route_weather(product, str(supplier_id) if supplier_id else None)
    return {"error": f"Unknown weather tool: {name}"}


async def periodic_supply_chain_weather_refresh(product: str = DEFAULT_PRODUCT) -> None:
    while True:
        try:
            await asyncio.to_thread(refresh_supply_chain_weather, product)
        except Exception:
            pass
        await asyncio.sleep(REFRESH_SECONDS)
