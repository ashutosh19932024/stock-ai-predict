from __future__ import annotations

from services.schemas import NewsItem
from services.x_service import XService


class SocialAgent:
    def __init__(self) -> None:
        self.x_service = XService()

    def collect(self, ticker: str, company: str) -> list[NewsItem]:
        return self.x_service.search_posts(ticker=ticker, query=company)
