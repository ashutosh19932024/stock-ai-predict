from __future__ import annotations

from services.schemas import PredictionResult
from utils.helpers import clamp


class Predictor:
    def predict(self, ticker: str, company: str, features: dict[str, float]) -> PredictionResult:
        sentiment_balance = features["positive_ratio"] - features["negative_ratio"]
        news_bias = sentiment_balance * (0.25 + 0.35 * features["avg_impact"])
        market_bias = features["momentum_5d"] * 1.15 + features["daily_return"] * 0.55
        volume_boost = (features["volume_ratio"] - 1.0) * 0.04
        uncertainty_penalty = features["volatility_20d"] * 0.45

        signal_score = news_bias + market_bias + volume_boost - uncertainty_penalty
        up_probability = clamp(0.5 + signal_score, 0.2, 0.8)

        evidence_support = min(features["news_count"], 5.0) / 5.0
        confidence = clamp(
            0.38 + abs(signal_score) * 0.9 + features["avg_confidence"] * 0.18 + evidence_support * 0.08,
            0.35,
            0.82,
        )

        volatility_scale = 1.2 + features["volatility_20d"] * 15
        expected_move_pct = round((up_probability - 0.5) * volatility_scale * 2.0, 2)

        if up_probability >= 0.6:
            outlook = "bullish"
        elif up_probability <= 0.4:
            outlook = "bearish"
        else:
            outlook = "neutral"

        drivers = []
        risks = []
        if features["positive_ratio"] > features["negative_ratio"]:
            drivers.append("Positive news flow outweighs negative coverage.")
        if features["momentum_5d"] > 0:
            drivers.append("Recent price momentum is supportive.")
        if features["volume_ratio"] > 1:
            drivers.append("Volume is above average, suggesting stronger market attention.")
        if features["negative_ratio"] > 0.3:
            risks.append("There is still meaningful negative headline pressure.")
        if features["volatility_20d"] > 0.03:
            risks.append("Elevated recent volatility can reduce signal reliability.")
        if not drivers:
            drivers.append("Signals are mixed, with no single dominant catalyst.")
        if not risks:
            risks.append("Unexpected macro or company-specific events can reverse short-term signals.")

        reasoning = (
            f"The model combines sentiment balance, impact strength, recent momentum, volatility, and volume. "
            f"Computed up probability is {up_probability:.2f}, implying a {outlook} short-term outlook."
        )

        return PredictionResult(
            ticker=ticker,
            company=company,
            outlook=outlook,
            up_probability=up_probability,
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            drivers=drivers,
            risks=risks,
            reasoning=reasoning,
        )
