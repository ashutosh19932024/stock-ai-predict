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


def _read_streamlit_secret(name: str) -> str:
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        return str(value).strip() if value else ""
    except Exception:
        return ""


def _read_setting(name: str, default: str = "") -> str:
    env_value = _clean_env_value(os.getenv(name))
    if env_value:
        return env_value

    secret_value = _clean_env_value(_read_streamlit_secret(name))
    if secret_value:
        return secret_value

    return default


def _detect_config_source() -> str:
    if active_env_file:
        return f".env file: {active_env_file}"

    known_keys = (
        "OPENAI_API_KEY",
        "NEWSAPI_KEY",
        "ALPHAVANTAGE_API_KEY",
        "X_BEARER_TOKEN",
        "USE_MOCK_DATA",
        "DEFAULT_MARKET",
    )
    if any(_clean_env_value(os.getenv(key)) for key in known_keys):
        return "environment variables"
    if any(_read_streamlit_secret(key) for key in known_keys):
        return "Streamlit secrets"
    return "No .env file, environment variables, or Streamlit secrets found."


@dataclass(slots=True)
class Settings:
    openai_api_key: str = _read_setting("OPENAI_API_KEY")
    openai_model: str = _read_setting("OPENAI_MODEL", "gpt-5-mini")
    newsapi_key: str = _read_setting("NEWSAPI_KEY")
    alphavantage_api_key: str = _read_setting("ALPHAVANTAGE_API_KEY")
    x_bearer_token: str = _read_setting("X_BEARER_TOKEN")
    use_mock_data: bool = _to_bool(_read_setting("USE_MOCK_DATA"), default=True)
    default_market: str = _read_setting("DEFAULT_MARKET", "US")
    config_source: str = _detect_config_source()
    env_file_used: str = _detect_config_source()


settings = Settings()
