"""Settings + pluggable runtime config.

Env vars are loaded once at startup. RUNTIME_CONFIG lets a teammate paste an
API key into the frontend (POST /config) and have it take effect immediately,
without restarting the server. get_key() checks RUNTIME_CONFIG first, then
falls back to the environment.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None

load_dotenv()

# Keys that can be set/overridden at runtime via POST /config.
PLUGGABLE_KEYS = [
    "JUA_API_KEY",
    "JUA_FORECAST_URL",
    "WEATHERAPI_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "CLICKHOUSE_HOST",
    "CLICKHOUSE_PORT",
    "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DATABASE",
    "AIRBYTE_API_KEY",
    "SLACK_WEBHOOK_URL",
    "SLACK_CHANNEL",
    "ACTIVE_MODEL",
]

RUNTIME_CONFIG: dict[str, str] = {}

AUTO_EXECUTE_USD_LIMIT = float(os.getenv("AUTO_EXECUTE_USD_LIMIT", "100000"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")


def get_key(name: str) -> str | None:
    """Return the active value for `name`, runtime override first."""
    value = RUNTIME_CONFIG.get(name) or os.getenv(name)
    return value or None


def set_keys(updates: dict[str, str]) -> None:
    for key, value in updates.items():
        if key not in PLUGGABLE_KEYS:
            continue
        if value:
            RUNTIME_CONFIG[key] = value
        else:
            RUNTIME_CONFIG.pop(key, None)


def get_active_model() -> str:
    """Which LLM provider drives the reasoning agents: 'claude' or 'deepseek'."""
    model = get_key("ACTIVE_MODEL")
    return model if model in ("claude", "deepseek") else "claude"


def integration_status() -> dict[str, bool | str]:
    return {
        "jua": get_key("JUA_API_KEY") is not None,
        "weatherapi": get_key("WEATHERAPI_KEY") is not None,
        "anthropic": get_key("ANTHROPIC_API_KEY") is not None,
        "deepseek": get_key("DEEPSEEK_API_KEY") is not None,
        "clickhouse": get_key("CLICKHOUSE_HOST") is not None,
        "airbyte": get_key("AIRBYTE_API_KEY") is not None,
        "slack": get_key("SLACK_WEBHOOK_URL") is not None,
        "active_model": get_active_model(),
    }
