"""Weather Agent — see docs/API_CONTRACT.md §1.

Tries Jua (real forecast) first, then Claude (parses event_text into
countries/severity), then a deterministic mock. Never raises.
"""

import httpx

from config import get_key

COUNTRY_COORDS = {
    "Germany": (51.1657, 10.4515),
    "Austria": (47.5162, 14.5501),
    "Poland": (51.9194, 19.1451),
    "Spain": (40.4637, -3.7492),
    "Sweden": (60.1282, 18.6435),
    "Netherlands": (52.1326, 5.2913),
}


def _score_weather(
    affected_countries: list[str],
    wind_kmh: float,
    precipitation_mm: float,
    temperature_c: float,
    source: str,
) -> dict:
    """Shared normalizer: turns raw weather numbers into severity/risk_level."""
    severity = min(1.0, (wind_kmh / 120) * 0.6 + (precipitation_mm / 80) * 0.4)
    if severity >= 0.66:
        risk_level = "severe"
    elif severity >= 0.4:
        risk_level = "high"
    else:
        risk_level = "moderate"

    return {
        "affected_countries": affected_countries,
        "wind_kmh": wind_kmh,
        "precipitation_mm": precipitation_mm,
        "temperature_c": temperature_c,
        "severity": round(severity, 2),
        "risk_level": risk_level,
        "source": source,
    }


def _mock_weather(affected: list[str]) -> dict:
    return _score_weather(affected, 92, 47, 4, source="mock")


def _jua_weather(event_text: str, affected: list[str]) -> dict | None:
    api_key = get_key("JUA_API_KEY")
    if not api_key:
        return None
    try:
        lat, lon = COUNTRY_COORDS[affected[0]]
        resp = httpx.get(
            "https://api.jua.ai/v1/forecast",
            params={"lat": lat, "lon": lon},
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return _score_weather(
            affected,
            wind_kmh=data["wind_kmh"],
            precipitation_mm=data["precipitation_mm"],
            temperature_c=data["temperature_c"],
            source="jua",
        )
    except Exception:
        return None


def _claude_affected_countries(event_text: str) -> list[str] | None:
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
                "model": "claude-sonnet-4-6",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Given this weather event description, return ONLY a "
                            "comma-separated list of which of these countries are "
                            f"affected: {', '.join(COUNTRY_COORDS)}.\n\n"
                            f"Event: {event_text}"
                        ),
                    }
                ],
            },
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        countries = [c.strip() for c in text.split(",")]
        affected = [c for c in countries if c in COUNTRY_COORDS]
        return affected or None
    except Exception:
        return None


def weather_agent(event_text: str) -> dict:
    affected = _claude_affected_countries(event_text) or ["Germany", "Austria", "Poland"]

    jua_result = _jua_weather(event_text, affected)
    if jua_result is not None:
        return jua_result

    return _mock_weather(affected)
