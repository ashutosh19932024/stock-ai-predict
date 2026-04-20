from __future__ import annotations

from services.official_service import OfficialSourceService
from services.schemas import NewsItem


class FilingsAgent:
    def __init__(self) -> None:
        self.official_service = OfficialSourceService()

    def collect(self, ticker: str) -> list[NewsItem]:
        return self.official_service.fetch_company_updates(ticker)
