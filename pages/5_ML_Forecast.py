from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ml.weekly_forecast import WeeklyForecastModel
from services.company_service import resolve_security
from services.historical_data_service import HistoricalMarketDataService


def filter_display_frame(frame: pd.DataFrame, preset: str, custom_start, custom_end) -> pd.DataFrame:
    if frame.empty:
        return frame

    end = frame.index.max()
    if preset == "Last week":
        start = end - pd.Timedelta(days=7)
    elif preset == "Last month":
        start = end - pd.Timedelta(days=30)
    elif preset == "Last 6 months":
        start = end - pd.Timedelta(days=183)
    elif preset == "Last year":
        start = end - pd.Timedelta(days=365)
    else:
        start = pd.to_datetime(custom_start)
        end = pd.to_datetime(custom_end)

    return frame[(frame.index >= start) & (frame.index <= end)].copy()


st.title("ML Forecast")
st.caption("Train a machine learning model on up to 10 years of daily data and predict next-week direction.")

with st.form("ml_forecast_form"):
    c1, c2 = st.columns([2, 1])
    identifier = c1.text_input("Ticker or Company", value="AAPL")
    years = c2.slider("History window (years)", min_value=3, max_value=10, value=10, step=1)
    submitted = st.form_submit_button("Run ML analysis", type="primary")

if submitted:
    resolved = resolve_security(identifier)
    history_result = HistoricalMarketDataService().get_daily_history(resolved.ticker, years=years)
    history = history_result.data.copy()

    if history.empty:
        st.error("No historical price data was returned for this security.")
    else:
        history["sma_20"] = history["close"].rolling(20).mean()
        history["sma_50"] = history["close"].rolling(50).mean()
        history["daily_return_pct"] = history["close"].pct_change() * 100

        try:
            forecast = WeeklyForecastModel().run(history)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.subheader(f"{resolved.company} ({resolved.ticker})")
            if not history_result.is_live:
                st.error(
                    "Live historical price data was not available for this symbol, so the page is showing synthetic fallback data. "
                    "That means the displayed close price will not match Google or your broker."
                )
                if history_result.diagnostics:
                    with st.expander("Live fetch diagnostics"):
                        for item in history_result.diagnostics:
                            st.write(f"- {item}")

            st.subheader("Tomorrow Forecast")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Tomorrow outlook", forecast.tomorrow.outlook.title())
            t2.metric("Probability of Up Move", f"{forecast.tomorrow.probability_up:.1%}")
            t3.metric("Predicted 1-Day Move", f"{forecast.tomorrow.predicted_return_pct:.2f}%")
            t4.metric("Tomorrow confidence", f"{forecast.tomorrow.confidence:.1%}")

            st.subheader("Next Week Forecast")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Next-week outlook", forecast.next_week.outlook.title())
            m2.metric("Probability of Up Move", f"{forecast.next_week.probability_up:.1%}")
            m3.metric("Predicted 5-Day Move", f"{forecast.next_week.predicted_return_pct:.2f}%")
            m4.metric("Model confidence", f"{forecast.next_week.confidence:.1%}")

            m5, m6, m7, m8 = st.columns(4)
            last_close_label = "Last close" if history_result.is_live else "Synthetic last close"
            m5.metric(last_close_label, f"{forecast.last_close:,.2f}")
            m6.metric("Training rows", f"{forecast.train_rows}")
            m7.metric("Tomorrow holdout accuracy", f"{forecast.tomorrow.holdout_accuracy:.1%}")
            m8.metric("Target week end", forecast.next_week.target_date)

            st.subheader("Final Recommendation")
            st.success(f"{forecast.final_recommendation}: {forecast.recommendation_reason}")

            st.markdown(
                f"""
**Data source:** `{history_result.source}`  
**Resolved from input:** `{identifier}` -> `{resolved.ticker}`  
**Live provider symbol:** `{history_result.provider_symbol or resolved.ticker}`  
**Matching mode:** `{resolved.matched_by}`  
**Resolved region:** `{resolved.region or 'local/default'}`
                """
            )

            st.subheader("Visualization")
            range_preset = st.selectbox(
                "Display period",
                ["Last week", "Last month", "Last 6 months", "Last year", "Custom"],
                index=2,
            )
            min_date = history.index.min().date()
            max_date = history.index.max().date()
            default_start = max(min_date, (max_date - timedelta(days=183)))
            custom_cols = st.columns(2)
            custom_start = custom_cols[0].date_input(
                "Custom start",
                value=default_start,
                min_value=min_date,
                max_value=max_date,
                disabled=range_preset != "Custom",
            )
            custom_end = custom_cols[1].date_input(
                "Custom end",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                disabled=range_preset != "Custom",
            )

            display_frame = filter_display_frame(history, range_preset, custom_start, custom_end)
            if display_frame.empty:
                st.info("No rows available for the selected display period.")
            else:
                price_fig = go.Figure()
                price_fig.add_trace(
                    go.Scatter(x=display_frame.index, y=display_frame["close"], name="Close", line=dict(width=2))
                )
                price_fig.add_trace(
                    go.Scatter(x=display_frame.index, y=display_frame["sma_20"], name="20D MA", line=dict(width=1.5))
                )
                price_fig.add_trace(
                    go.Scatter(x=display_frame.index, y=display_frame["sma_50"], name="50D MA", line=dict(width=1.5))
                )
                price_fig.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20), title="Price trend")
                st.plotly_chart(price_fig, use_container_width=True)

                chart_cols = st.columns(2)
                volume_fig = px.bar(
                    display_frame.reset_index(),
                    x="date",
                    y="volume",
                    title="Volume",
                )
                volume_fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
                chart_cols[0].plotly_chart(volume_fig, use_container_width=True)

                returns_fig = px.line(
                    display_frame.reset_index(),
                    x="date",
                    y="daily_return_pct",
                    title="Daily return %",
                )
                returns_fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
                chart_cols[1].plotly_chart(returns_fig, use_container_width=True)

            st.subheader("Model diagnostics")
            diag_cols = st.columns(2)
            history_tail = forecast.next_week.prediction_history.reset_index().rename(columns={"index": "date"})
            prob_fig = px.line(
                history_tail.tail(120),
                x=history_tail.tail(120).columns[0],
                y="predicted_prob_up",
                title="Recent holdout predicted probability of up move",
            )
            prob_fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
            diag_cols[0].plotly_chart(prob_fig, use_container_width=True)

            importance_fig = px.bar(
                forecast.feature_importance.head(10),
                x="importance",
                y="feature",
                orientation="h",
                title="Top feature importance",
            )
            importance_fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20), yaxis=dict(categoryorder="total ascending"))
            diag_cols[1].plotly_chart(importance_fig, use_container_width=True)

            st.subheader("Selected-period data")
            if not display_frame.empty:
                st.dataframe(
                    display_frame.reset_index()[["date", "open", "high", "low", "close", "volume", "daily_return_pct"]]
                    .sort_values("date", ascending=False),
                    width="stretch",
                    hide_index=True,
                )

            st.subheader("Recent model backtest rows")
            backtest_view = forecast.next_week.prediction_history.reset_index().rename(columns={"index": "date"})
            st.dataframe(
                backtest_view.tail(60)[
                    [
                        "date",
                        "close",
                        "target_return_5d",
                        "target_up_5d",
                        "predicted_prob_up",
                        "predicted_label",
                        "predicted_return_pct",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )
