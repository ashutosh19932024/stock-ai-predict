from __future__ import annotations

import hashlib
import re

from services.schemas import EventCluster, SentimentRecord


SOURCE_WEIGHTS = {
    "official": 1.0,
    "news": 0.75,
    "social": 0.35,
}
SENTIMENT_SIGN = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


class EventExtractionAgent:
    def extract(self, ticker: str, company: str, evidence: list[SentimentRecord]) -> list[EventCluster]:
        buckets: dict[str, list[SentimentRecord]] = {}
        for item in evidence:
            key = self._cluster_key(item.title)
            buckets.setdefault(key, []).append(item)

        events: list[EventCluster] = []
        for key, records in buckets.items():
            weighted_score = 0.0
            sources: list[str] = []
            sentiment_totals = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
            for record in records:
                weight = SOURCE_WEIGHTS.get(record.source_type, 0.5)
                signed = SENTIMENT_SIGN.get(record.sentiment, 0.0) * record.impact_strength * record.confidence * weight
                weighted_score += signed
                sentiment_totals[record.sentiment] += abs(signed)
                if record.source not in sources:
                    sources.append(record.source)

            dominant_sentiment = max(sentiment_totals, key=sentiment_totals.get)
            top_title = max(records, key=lambda item: item.impact_strength).title
            summary = max(records, key=lambda item: len(item.summary)).summary
            events.append(
                EventCluster(
                    event_id=hashlib.md5(key.encode("utf-8")).hexdigest()[:10],
                    ticker=ticker,
                    company=company,
                    headline=top_title,
                    summary=summary,
                    sentiment=dominant_sentiment,
                    weighted_score=weighted_score,
                    article_count=len(records),
                    sources=sources,
                )
            )

        return sorted(events, key=lambda item: abs(item.weighted_score), reverse=True)

    def _cluster_key(self, title: str) -> str:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return " ".join(normalized.split()[:8]) or "misc"
