from __future__ import annotations

import streamlit as st

from utils.config import settings


def get_active_market() -> str:
    try:
        market = st.session_state.get("selected_market", settings.default_market)
    except Exception:
        market = settings.default_market
    normalized = str(market or settings.default_market).strip()
    if normalized.upper() in {"IN", "INDIA"}:
        return "India"
    return "US"
