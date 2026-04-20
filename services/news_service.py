from __future__ import annotations

import re
from email.utils import parsedate_to_datetime
from html import unescape
from xml.etree import ElementTree

import requests
from services.company_service import get_historical_symbol_candidates
from services.mock_data import MOCK_NEWS
from services.schemas import NewsItem
from utils.config import settings
from utils.dedupe import dedupe_records
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsService:
    base_url = "https://newsapi.org/v2/everything"
    yahoo_rss_url = "https://feeds.finance.yahoo.com/rss/2.0/headline"

    def _mock_results(self, query: str, ticker: str | None = None) -> list[NewsItem]:
        records = MOCK_NEWS.get((ticker or "").upper(), [])
        if not records and query:
            records = [item for items in MOCK_NEWS.values() for item in items if query.lower() in item["title"].lower()]
        return [NewsItem(**item) for item in dedupe_records(records)]

    def search(self, query: str, ticker: str | None = None, page_size: int = 10) -> list[NewsItem]:
        if settings.use_mock_data:
            return self._mock_results(query=query, ticker=ticker)
        if not settings.newsapi_key:
            logger.warning("News API key missing; trying Yahoo Finance RSS for %s.", query)
            return self._yahoo_finance_results(query=query, ticker=ticker, page_size=page_size)

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
            return self._yahoo_finance_results(query=query, ticker=ticker, page_size=page_size)

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
        if articles:
            return articles

        logger.info("News API returned no articles for %s; trying Yahoo Finance RSS.", query)
        return self._yahoo_finance_results(query=query, ticker=ticker, page_size=page_size)

    def _yahoo_finance_results(self, query: str, ticker: str | None, page_size: int) -> list[NewsItem]:
        symbols = get_historical_symbol_candidates(ticker or query)
        if ticker and ticker.upper() not in symbols:
            symbols.append(ticker.upper())

        records: list[dict[str, str]] = []
        for symbol in symbols[:4]:
            records.extend(self._fetch_yahoo_rss_symbol(symbol=symbol, query=query, ticker=ticker))
            if len(records) >= page_size:
                break

        return [NewsItem(**item) for item in dedupe_records(records)[:page_size]]

    def _fetch_yahoo_rss_symbol(self, symbol: str, query: str, ticker: str | None) -> list[dict[str, str]]:
        params = {
            "s": symbol,
            "region": "US",
            "lang": "en-US",
        }
        try:
            response = requests.get(self.yahoo_rss_url, params=params, timeout=15)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError) as exc:
            logger.warning("Yahoo Finance RSS request failed for %s: %s", symbol, exc)
            return []

        items = []
        for item in root.findall(".//item"):
            title = self._clean_text(item.findtext("title", default="Untitled"))
            link = item.findtext("link", default="")
            description = self._clean_text(item.findtext("description", default=""))
            published_at = self._format_rss_date(item.findtext("pubDate", default=""))
            if not title or not link:
                continue
            items.append(
                {
                    "source": f"Yahoo Finance RSS ({symbol})",
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "content": description,
                    "ticker": ticker or symbol,
                    "company": query,
                    "source_type": "news",
                }
            )
        return items

    def _clean_text(self, value: str) -> str:
        cleaned = unescape(value or "")
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _format_rss_date(self, value: str) -> str:
        if not value:
            return ""
        try:
            return parsedate_to_datetime(value).isoformat()
        except (TypeError, ValueError):
            return value
