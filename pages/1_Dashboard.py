from __future__ import annotations

import pandas as pd
import streamlit as st
from agents.orchestrator import StockAnalysisOrchestrator

st.title("Dashboard")
st.caption("Quick multi-ticker signal monitor")

watchlist = st.session_state.get("watchlist", ["AAPL", "TSLA", "NVDA"])
run = st.button("Refresh signals", type="primary")

if run:
    orchestrator = StockAnalysisOrchestrator()
    rows = []
    with st.spinner("Analyzing watchlist..."):
        for ticker in watchlist:
            result = orchestrator.run(ticker)
            rows.append(
                {
                    "Ticker": result.prediction.ticker,
                    "Company": result.prediction.company,
                    "Outlook": result.prediction.outlook,
                    "Up Probability": round(result.prediction.up_probability, 2),
                    "Confidence": round(result.prediction.confidence, 2),
                    "Expected Move %": result.prediction.expected_move_pct,
                    "Evidence Count": len(result.evidence),
                }
            )
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
    if not df.empty:
        st.bar_chart(df.set_index("Ticker")["Up Probability"])
else:
    st.write("Click **Refresh signals** to run the agent across your watchlist.")
