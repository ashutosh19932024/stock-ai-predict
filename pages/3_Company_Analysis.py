from __future__ import annotations

import pandas as pd
import streamlit as st
from agents.orchestrator import StockAnalysisOrchestrator
from utils.config import settings
from utils.runtime_context import get_active_market

st.title("Company Analysis")
st.caption(f"Active market preference: {get_active_market()}")

identifier = st.text_input("Ticker or Company", value="AAPL").strip()
if st.button("Analyze company", type="primary"):
    result = StockAnalysisOrchestrator().run(identifier)

    c1, c2, c3 = st.columns(3)
    c1.metric("Outlook", result.prediction.outlook.title())
    c2.metric("Up Probability", f"{result.prediction.up_probability:.0%}")
    c3.metric("Confidence", f"{result.prediction.confidence:.0%}")

    st.write(result.answer)

    if not settings.use_mock_data and not result.evidence:
        st.warning(
            "No live evidence was returned for this company. The prediction is therefore neutral/low-confidence "
            "instead of using dummy mock news. Check NewsAPI credentials, API quota, Yahoo Finance RSS availability, "
            "and Streamlit secrets."
        )
        if result.diagnostics:
            with st.expander("Live evidence diagnostics"):
                for item in result.diagnostics:
                    st.write(f"- {item}")

    st.subheader("Drivers")
    for item in result.prediction.drivers:
        st.write(f"- {item}")

    st.subheader("Risks")
    for item in result.prediction.risks:
        st.write(f"- {item}")

    st.subheader("Evidence table")
    df = pd.DataFrame([e.model_dump() for e in result.evidence])
    if df.empty:
        st.info("No evidence rows available from live providers.")
    else:
        display_columns = [
            "published_at",
            "source",
            "source_type",
            "sentiment",
            "impact_strength",
            "title",
            "url",
        ]
        display_df = df[display_columns].copy()
        display_df["url"] = display_df["url"].fillna("")
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "published_at": st.column_config.DatetimeColumn("published_at"),
                "impact_strength": st.column_config.NumberColumn("impact_strength", format="%.2f"),
                "url": st.column_config.LinkColumn("url", display_text="Open source"),
            },
        )

    if not df.empty:
        counts = df["sentiment"].value_counts()
        st.bar_chart(counts)
