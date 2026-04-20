from __future__ import annotations

import pandas as pd
import streamlit as st

from agents.advanced_screener_agent import AdvancedScreenerAgent
from agents.planner_agent import PlannerAgent


st.title("Advanced Screener")
st.caption("Planner + specialists flow for ranking tomorrow-ready stock candidates across US and Indian universes.")

default_prompt = (
    "Analyze top 10 large cap, mid cap, and small cap stocks to consider purchasing tomorrow "
    "in Indian and US markets using ML and news analysis."
)
prompt = st.text_area("Planner request", value=default_prompt, height=120)

form_cols = st.columns(3)
markets = form_cols[0].multiselect("Markets", ["US", "India"], default=["US", "India"])
cap_buckets = form_cols[1].multiselect("Cap buckets", ["large", "mid", "small"], default=["large", "mid", "small"])
top_n = form_cols[2].slider("Top results", min_value=5, max_value=20, value=10, step=1)

if st.button("Run advanced screener", type="primary"):
    plan = PlannerAgent().plan(prompt)
    st.info(f"Planner decision: `{plan.task}` ({plan.confidence:.0%}) - {plan.rationale}")

    if plan.task != "market_screener":
        st.warning("This page currently executes the market screener workflow. Try a screener-style prompt.")
    elif not markets or not cap_buckets:
        st.warning("Select at least one market and one cap bucket.")
    else:
        with st.spinner("Running planner + specialist agents across the selected universe..."):
            results = AdvancedScreenerAgent().rank(markets=markets, cap_buckets=cap_buckets, top_n=top_n)

        if not results:
            st.warning("No screener results were produced. Live providers may be unavailable.")
        else:
            ranking_df = pd.DataFrame(
                [
                    {
                        "Rank": idx + 1,
                        "Ticker": item.ticker,
                        "Company": item.company,
                        "Market": item.market,
                        "Cap Bucket": item.cap_bucket,
                        "Overall Score": round(item.overall_score, 4),
                        "Tomorrow Up %": round(item.tomorrow_up_probability * 100, 1),
                        "Next Week Up %": round(item.next_week_up_probability * 100, 1),
                        "Tomorrow Move %": round(item.expected_tomorrow_move_pct, 2),
                        "Week Move %": round(item.expected_week_move_pct, 2),
                        "Recommendation": item.recommendation,
                    }
                    for idx, item in enumerate(results)
                ]
            )
            st.subheader("Top Ranked Candidates")
            st.dataframe(ranking_df, width="stretch", hide_index=True)

            st.subheader("Detailed Breakdown")
            for idx, item in enumerate(results, start=1):
                with st.expander(f"{idx}. {item.company} ({item.ticker}) | {item.market} | {item.cap_bucket}"):
                    st.write(f"Recommendation: **{item.recommendation}**")
                    st.write(
                        f"Tomorrow up probability: **{item.tomorrow_up_probability:.0%}** | "
                        f"Next-week up probability: **{item.next_week_up_probability:.0%}**"
                    )
                    st.write(
                        f"Expected tomorrow move: **{item.expected_tomorrow_move_pct:.2f}%** | "
                        f"Expected next-week move: **{item.expected_week_move_pct:.2f}%**"
                    )

                    st.write("Reasons:")
                    for reason in item.reasons:
                        st.write(f"- {reason}")

                    if item.top_events:
                        st.write("Top events:")
                        for event in item.top_events:
                            st.write(
                                f"- {event.headline} | {event.sentiment} | weighted score {event.weighted_score:.3f} | "
                                f"{event.article_count} article(s)"
                            )

                    if item.diagnostics:
                        st.write("Diagnostics:")
                        for line in item.diagnostics[:8]:
                            st.write(f"- {line}")
