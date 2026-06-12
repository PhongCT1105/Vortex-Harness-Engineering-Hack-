"""Weather Agent.

Pipeline order:
1. AI parses the trigger into affected supplier countries.
2. Jua is used first when configured.
3. Open-Meteo is used as a real no-key weather source when Jua is unavailable.
4. A rules estimate is used only if live weather cannot be reached.

The function never raises into the orchestrator.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

import httpx

from ai_agent import llm_json
from config import get_key

COUNTRY_COORDS = {
    "Germany": (51.1657, 10.4515),
    "Austria": (47.5162, 14.5501),
    "Poland": (51.9194, 19.1451),
    "Spain": (40.4637, -3.7492),
    "Sweden": (60.1282, 18.6435),
    "Netherlands": (52.1326, 5.2913),
}

COUNTRY_ALIASES = {
    "germany": "Germany",
    "deutschland": "Germany",
    "austria": "Austria",
    "poland": "Poland",
    "spain": "Spain",
    "sweden": "Sweden",
    "netherlands": "Netherlands",
    "holland": "Netherlands",
    "dutch": "Netherlands",
}


def _score_weather(
    affected_countries: list[str],
    wind_kmh: float,
    precipitation_mm: float,
    temperature_c: float,
    source: str,
    confidence: float = 0.8,
) -> dict:
    severity = min(1.0, (wind_kmh / 120) * 0.6 + (precipitation_mm / 80) * 0.4)
    if temperature_c <= -5:
        severity = min(1.0, severity + 0.12)
    if severity >= 0.66:
        risk_level = "severe"
    elif severity >= 0.4:
        risk_level = "high"
    else:
        risk_level = "moderate"

    return {
        "affected_countries": affected_countries,
        "wind_kmh": round(wind_kmh, 1),
        "precipitation_mm": round(precipitation_mm, 1),
        "temperature_c": round(temperature_c, 1),
        "severity": round(severity, 2),
        "risk_level": risk_level,
        "source": source,
        "confidence": round(confidence, 2),
    }


def _keyword_countries(event_text: str) -> list[str]:
    normalized = event_text.lower()
    countries = []
    for alias, country in COUNTRY_ALIASES.items():
        if alias in normalized and country not in countries:
            countries.append(country)

    regional_terms = {
        ("central europe", "european storm", "storm front"): ["Germany", "Austria", "Poland"],
        ("benelux", "dutch", "netherlands"): ["Netherlands", "Germany"],
        ("nordic", "scandinavia", "snowfall"): ["Sweden", "Poland"],
        ("iberia", "heatwave", "spain"): ["Spain"],
    }
    for terms, mapped in regional_terms.items():
        if any(term in normalized for term in terms):
            for country in mapped:
                if country not in countries:
                    countries.append(country)

    return countries


def _ai_countries(event_text: str) -> tuple[list[str], float]:
    prompt = f"""
You are a weather-risk parser for a supply-chain incident system.
Return strict JSON only:
{{
  "affected_countries": ["subset of: {', '.join(COUNTRY_COORDS)}"],
  "confidence": 0.0,
  "reason": "short reason"
}}

Trigger event:
{event_text}
"""
    data = llm_json(prompt, max_tokens=250)
    if not data:
        return [], 0.0

    raw = data.get("affected_countries", [])
    if not isinstance(raw, list):
        return [], 0.0
    countries = []
    for item in raw:
        country = str(item).strip()
        if country in COUNTRY_COORDS and country not in countries:
            countries.append(country)
    try:
        confidence = float(data.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    return countries, max(0.0, min(1.0, confidence))


def _affected_countries(event_text: str) -> tuple[list[str], float]:
    ai_countries, confidence = _ai_countries(event_text)
    keyword_countries = _keyword_countries(event_text)

    merged = []
    for country in ai_countries + keyword_countries:
        if country not in merged:
            merged.append(country)

    if merged:
        return merged, max(confidence, 0.65 if keyword_countries else 0.0)
    return list(COUNTRY_COORDS), 0.25


def _find_number(data: Any, names: set[str]) -> float | None:
    if isinstance(data, dict):
        for key, value in data.items():
            normalized = str(key).lower()
            if normalized in names and isinstance(value, int | float):
                return float(value)
            found = _find_number(value, names)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_number(item, names)
            if found is not None:
                return found
    return None


def _jua_country_weather(country: str) -> dict | None:
    api_key = get_key("JUA_API_KEY")
    if not api_key:
        return None

    lat, lon = COUNTRY_COORDS[country]
    url = get_key("JUA_FORECAST_URL") or "https://api.jua.ai/v1/forecast"
    try:
        resp = httpx.get(
            url,
            params={"lat": lat, "lon": lon},
            headers={"X-API-Key": api_key, "Authorization": f"Bearer {api_key}"},
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        wind = _find_number(data, {"wind_kmh", "wind_speed_10m", "wind_speed", "wind"})
        precip = _find_number(
            data,
            {"precipitation_mm", "precipitation", "rain", "rain_mm", "total_precipitation"},
        )
        temp = _find_number(data, {"temperature_c", "temperature_2m", "temperature", "temp"})
        if wind is None or precip is None or temp is None:
            return None
        return {"wind_kmh": wind, "precipitation_mm": precip, "temperature_c": temp}
    except Exception:
        return None


def _open_meteo_country_weather(country: str) -> dict | None:
    lat, lon = COUNTRY_COORDS[country]
    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,wind_speed_10m",
                "forecast_days": 1,
            },
            timeout=12,
        )
        resp.raise_for_status()
        current = resp.json()["current"]
        return {
            "wind_kmh": float(current["wind_speed_10m"]),
            "precipitation_mm": float(current["precipitation"]),
            "temperature_c": float(current["temperature_2m"]),
        }
    except Exception:
        return None


def _live_weather(affected: list[str]) -> tuple[str, list[dict]]:
    jua_rows = [_jua_country_weather(country) for country in affected]
    jua_rows = [row for row in jua_rows if row is not None]
    if jua_rows:
        return "jua", jua_rows

    open_meteo_rows = [_open_meteo_country_weather(country) for country in affected]
    open_meteo_rows = [row for row in open_meteo_rows if row is not None]
    if open_meteo_rows:
        return "open-meteo", open_meteo_rows

    return "rules", []


def _event_hazard_weather(event_text: str) -> dict | None:
    text = event_text.lower()
    wind = 0.0
    precip = 0.0
    temp: float | None = None

    if any(term in text for term in ["storm", "hurricane", "typhoon", "wind"]):
        wind = 95.0
        precip = 30.0
    if any(term in text for term in ["flood", "rain", "monsoon"]):
        precip = max(precip, 65.0)
        wind = max(wind, 45.0)
    if any(term in text for term in ["snow", "blizzard", "cold snap", "freeze"]):
        temp = -7.0
        precip = max(precip, 35.0)
        wind = max(wind, 55.0)
    if any(term in text for term in ["heat", "wildfire", "drought"]):
        temp = 38.0
        wind = max(wind, 40.0)

    if wind == 0.0 and precip == 0.0 and temp is None:
        return None

    return {
        "wind_kmh": wind or 35.0,
        "precipitation_mm": precip or 8.0,
        "temperature_c": temp if temp is not None else 12.0,
    }


def _rules_weather(event_text: str) -> dict:
    return _event_hazard_weather(event_text) or {
        "wind_kmh": 35.0,
        "precipitation_mm": 8.0,
        "temperature_c": 12.0,
    }


def weather_agent(event_text: str) -> dict:
    affected, country_confidence = _affected_countries(event_text)
    source, rows = _live_weather(affected)
    trigger_hazard = _event_hazard_weather(event_text)

    if not rows:
        rows = [_rules_weather(event_text)]
    elif trigger_hazard is not None:
        rows.append(trigger_hazard)
        source = f"{source}+event"

    return _score_weather(
        affected,
        wind_kmh=max(row["wind_kmh"] for row in rows),
        precipitation_mm=max(row["precipitation_mm"] for row in rows),
        temperature_c=mean(row["temperature_c"] for row in rows),
        source=source,
        confidence=country_confidence,
    )
