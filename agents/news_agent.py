from __future__ import annotations

from services.news_service import NewsService
from services.official_service import OfficialSourceService
from services.x_service import XService
from services.schemas import NewsItem
from utils.dedupe import dedupe_records


class NewsAgent:
    def __init__(self) -> None:
        self.news_service = NewsService()
        self.official_service = OfficialSourceService()
        self.x_service = XService()

    def collect(self, ticker: str, company: str) -> list[NewsItem]:
        records: list[NewsItem] = []
        records.extend(self.news_service.search(query=company, ticker=ticker))
        records.extend(self.official_service.fetch_company_updates(ticker))
        records.extend(self.x_service.search_posts(ticker=ticker, query=company))
        deduped = dedupe_records([item.model_dump() for item in records])
        return [NewsItem(**item) for item in deduped]
