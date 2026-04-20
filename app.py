from __future__ import annotations

import sys
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from db.repository import JsonRepository
from utils.config import settings

if get_script_run_ctx() is None:
    print("Please start this app with: streamlit run app.py")
    sys.exit(0)

st.set_page_config(page_title="Agentic Stock News AI", page_icon="📈", layout="wide")

repo = JsonRepository()
watchlist = repo.read().get("watchlist", ["AAPL", "TSLA", "NVDA"])

if "watchlist" not in st.session_state:
    st.session_state.watchlist = watchlist

st.title("📈 Agentic Stock News AI")
st.caption("News + social + official updates + market snapshot → next-day directional signal")

with st.sidebar:
    st.header("Settings")
    st.write(f"Mock data: **{settings.use_mock_data}**")
    st.write(f"Default market: **{settings.default_market}**")
    st.caption(f"Config source: `{settings.config_source}`")
    if not settings.newsapi_key or not settings.alphavantage_api_key:
        st.warning("Live mode still needs valid `NEWSAPI_KEY` and `ALPHAVANTAGE_API_KEY` in `.env`, environment variables, or Streamlit secrets.")
    ticker = st.text_input("Add ticker to watchlist", value="")
    if st.button("Add", width="stretch") and ticker:
        t = ticker.upper().strip()
        if t not in st.session_state.watchlist:
            st.session_state.watchlist.append(t)
            repo.write({"watchlist": st.session_state.watchlist})
            st.success(f"Added {t}")

col1, col2 = st.columns([1.6, 1])
with col1:
    st.subheader("What this app does")
    st.markdown(
        """
- Collects news, social chatter, and official company updates
- Classifies each item as positive, neutral, or negative
- Combines text signals with simple price and volume features
- Produces a next-day outlook: bullish, neutral, or bearish
- Explains the result in chat form
        """
    )
with col2:
    st.subheader("Current watchlist")
    st.dataframe({"Ticker": st.session_state.watchlist}, width="stretch", hide_index=True)

st.info("Open the pages from the left sidebar: Dashboard, Chat, Company Analysis, Backtest, ML Forecast, and Advanced Screener.")
