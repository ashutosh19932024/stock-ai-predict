from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

active_env_file = ENV_FILE if ENV_FILE.exists() else None
if active_env_file:
    load_dotenv(dotenv_path=active_env_file, override=True)


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean_env_value(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = value.strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    placeholder_prefixes = ("your_", "placeholder", "replace_me", "example")
    if lowered.startswith(placeholder_prefixes):
        return ""
    return cleaned


@dataclass(slots=True)
class Settings:
    openai_api_key: str = _clean_env_value(os.getenv("OPENAI_API_KEY"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    newsapi_key: str = _clean_env_value(os.getenv("NEWSAPI_KEY"))
    alphavantage_api_key: str = _clean_env_value(os.getenv("ALPHAVANTAGE_API_KEY"))
    x_bearer_token: str = _clean_env_value(os.getenv("X_BEARER_TOKEN"))
    use_mock_data: bool = _to_bool(os.getenv("USE_MOCK_DATA"), default=True)
    default_market: str = os.getenv("DEFAULT_MARKET", "US")
    env_file_used: str = str(active_env_file) if active_env_file else "No .env file found. Create a .env file in the project root."


settings = Settings()
