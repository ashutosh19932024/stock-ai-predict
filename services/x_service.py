from __future__ import annotations

from services.mock_data import MOCK_NEWS
from services.schemas import NewsItem
from utils.config import settings


class XService:
    """Stub for X/Twitter integration.

    To make this production-ready, replace mock output with official X API calls.
    """

    def search_posts(self, ticker: str, query: str | None = None) -> list[NewsItem]:
        if settings.use_mock_data:
            records = [item for item in MOCK_NEWS.get(ticker.upper(), []) if item.get("source_type") == "social"]
            return [NewsItem(**item) for item in records]
        if not settings.x_bearer_token:
            return []

        # Production X API integration goes here.
        return []
