from __future__ import annotations

from services.openai_service import OpenAIService
from services.schemas import NewsItem, SentimentRecord
from utils.helpers import clamp


POSITIVE_WORDS = {
    "strong", "growth", "beat", "expands", "up", "gain", "bullish", "demand", "improves", "stable", "profit"
}
NEGATIVE_WORDS = {
    "weak", "pressure", "down", "fall", "bearish", "cuts", "risk", "lawsuit", "margin", "decline", "loss"
}


class SentimentAgent:
    def __init__(self) -> None:
        self.openai = OpenAIService()

    def analyze(self, item: NewsItem) -> SentimentRecord:
        structured = self.openai.structured_sentiment(
            text=f"{item.title}\n\n{item.content}",
            ticker=item.ticker or "UNKNOWN",
            company=item.company or (item.ticker or "UNKNOWN"),
        )
        if structured:
            structured = self._sanitize_structured_sentiment(structured, item)
            return SentimentRecord(
                **structured,
                source=item.source,
                source_type=item.source_type,
                published_at=item.published_at,
                title=item.title,
                url=item.url,
            )

        text = f"{item.title} {item.content}".lower()
        positive_hits = sum(word in text for word in POSITIVE_WORDS)
        negative_hits = sum(word in text for word in NEGATIVE_WORDS)

        if positive_hits > negative_hits:
            sentiment = "positive"
        elif negative_hits > positive_hits:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        impact_strength = clamp(0.45 + 0.1 * abs(positive_hits - negative_hits), 0.35, 0.9)
        confidence = clamp(0.55 + 0.08 * (positive_hits + negative_hits), 0.5, 0.92)
        return SentimentRecord(
            ticker=item.ticker or "UNKNOWN",
            company=item.company or (item.ticker or "UNKNOWN"),
            sentiment=sentiment,
            event_type="general_news",
            impact_strength=impact_strength,
            horizon_days=1,
            confidence=confidence,
            summary=item.content[:240],
            source=item.source,
            source_type=item.source_type,
            published_at=item.published_at,
            title=item.title,
            url=item.url,
        )

    def _sanitize_structured_sentiment(self, structured: dict, item: NewsItem) -> dict:
        sentiment = str(structured.get("sentiment", "neutral")).lower()
        if sentiment not in {"positive", "neutral", "negative"}:
            sentiment = "neutral"

        return {
            "ticker": str(structured.get("ticker") or item.ticker or "UNKNOWN"),
            "company": str(structured.get("company") or item.company or item.ticker or "UNKNOWN"),
            "sentiment": sentiment,
            "event_type": str(structured.get("event_type") or "general_news"),
            "impact_strength": clamp(self._safe_float(structured.get("impact_strength"), 0.45), 0.0, 1.0),
            "horizon_days": int(clamp(self._safe_float(structured.get("horizon_days"), 1), 1, 30)),
            "confidence": clamp(self._safe_float(structured.get("confidence"), 0.55), 0.0, 1.0),
            "summary": str(structured.get("summary") or item.content[:240] or item.title),
        }

    def _safe_float(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
