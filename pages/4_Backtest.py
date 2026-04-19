from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

st.title("Backtest")
st.caption("This page shows a simple placeholder simulation for the starter project.")

n = st.slider("Number of simulated predictions", min_value=30, max_value=300, value=120, step=10)
seed = st.number_input("Random seed", min_value=1, max_value=9999, value=42)

rng = np.random.default_rng(seed)
actual = rng.integers(0, 2, size=n)
prob = rng.uniform(0.25, 0.80, size=n)
pred = (prob >= 0.5).astype(int)
accuracy = float((pred == actual).mean())

st.metric("Simulated accuracy", f"{accuracy:.2%}")

df = pd.DataFrame({"actual": actual, "predicted_prob_up": prob, "predicted_label": pred})
st.dataframe(df.head(25), width="stretch", hide_index=True)
st.line_chart(df["predicted_prob_up"])

st.warning("Replace this placeholder page with a real historical backtest once you store labeled outcomes.")
