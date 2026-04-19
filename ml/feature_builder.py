from __future__ import annotations

from services.schemas import PriceSnapshot, SentimentRecord


class FeatureBuilder:
    def build(self, sentiments: list[SentimentRecord], price: PriceSnapshot) -> dict[str, float]:
        if not sentiments:
            return {
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "avg_impact": 0.0,
                "avg_confidence": 0.0,
                "news_count": 0.0,
                "daily_return": price.daily_return,
                "momentum_5d": price.momentum_5d,
                "volatility_20d": price.volatility_20d,
                "volume_ratio": price.volume / price.avg_volume if price.avg_volume else 1.0,
            }

        positive = [x for x in sentiments if x.sentiment == "positive"]
        negative = [x for x in sentiments if x.sentiment == "negative"]
        n = len(sentiments)

        return {
            "positive_ratio": len(positive) / n,
            "negative_ratio": len(negative) / n,
            "avg_impact": sum(x.impact_strength for x in sentiments) / n,
            "avg_confidence": sum(x.confidence for x in sentiments) / n,
            "news_count": float(n),
            "daily_return": price.daily_return,
            "momentum_5d": price.momentum_5d,
            "volatility_20d": price.volatility_20d,
            "volume_ratio": price.volume / price.avg_volume if price.avg_volume else 1.0,
        }
