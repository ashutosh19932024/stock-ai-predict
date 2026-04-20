from __future__ import annotations

import requests
from services.mock_data import MOCK_NEWS
from services.schemas import NewsItem
from utils.config import settings
from utils.dedupe import dedupe_records
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsService:
    base_url = "https://newsapi.org/v2/everything"

    def _mock_results(self, query: str, ticker: str | None = None) -> list[NewsItem]:
        records = MOCK_NEWS.get((ticker or "").upper(), [])
        if not records and query:
            records = [item for items in MOCK_NEWS.values() for item in items if query.lower() in item["title"].lower()]
        return [NewsItem(**item) for item in dedupe_records(records)]

    def search(self, query: str, ticker: str | None = None, page_size: int = 10) -> list[NewsItem]:
        if settings.use_mock_data:
            return self._mock_results(query=query, ticker=ticker)
        if not settings.newsapi_key:
            logger.warning("News API key missing; returning no live news for %s.", query)
            return []

        params = {
            "q": f'("{query}" OR {ticker}) stock',
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": settings.newsapi_key,
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning("News API request failed for %s: %s", query, exc)
            return []

        articles = []
        for article in payload.get("articles", []):
            articles.append(
                NewsItem(
                    source=article.get("source", {}).get("name", "Unknown"),
                    title=article.get("title", "Untitled"),
                    url=article.get("url", ""),
                    published_at=article.get("publishedAt", ""),
                    content=article.get("content") or article.get("description") or "",
                    ticker=ticker,
                    company=query,
                    source_type="news",
                )
            )
        return articles
