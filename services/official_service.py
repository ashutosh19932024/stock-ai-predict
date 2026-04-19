from __future__ import annotations

from services.mock_data import MOCK_NEWS
from services.schemas import NewsItem


class OfficialSourceService:
    def fetch_company_updates(self, ticker: str) -> list[NewsItem]:
        records = [item for item in MOCK_NEWS.get(ticker.upper(), []) if item.get("source_type") == "official"]
        return [NewsItem(**item) for item in records]
