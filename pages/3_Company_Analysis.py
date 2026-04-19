from __future__ import annotations

import pandas as pd
import streamlit as st
from agents.orchestrator import StockAnalysisOrchestrator

st.title("Company Analysis")

identifier = st.text_input("Ticker or Company", value="AAPL").strip()
if st.button("Analyze company", type="primary"):
    result = StockAnalysisOrchestrator().run(identifier)

    c1, c2, c3 = st.columns(3)
    c1.metric("Outlook", result.prediction.outlook.title())
    c2.metric("Up Probability", f"{result.prediction.up_probability:.0%}")
    c3.metric("Confidence", f"{result.prediction.confidence:.0%}")

    st.write(result.answer)

    st.subheader("Drivers")
    for item in result.prediction.drivers:
        st.write(f"- {item}")

    st.subheader("Risks")
    for item in result.prediction.risks:
        st.write(f"- {item}")

    st.subheader("Evidence table")
    df = pd.DataFrame([e.model_dump() for e in result.evidence])
    st.dataframe(df, width="stretch", hide_index=True)

    if not df.empty:
        counts = df["sentiment"].value_counts()
        st.bar_chart(counts)
