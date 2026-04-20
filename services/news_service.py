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
    google_rss_url = "https://news.google.com/rss/search"

    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    def _note(self, message: str) -> None:
        self.diagnostics.append(message)
        logger.info(message)

    def _mock_results(self, query: str, ticker: str | None = None) -> list[NewsItem]:
        records = MOCK_NEWS.get((ticker or "").upper(), [])
        if not records and query:
            records = [item for items in MOCK_NEWS.values() for item in items if query.lower() in item["title"].lower()]
        return [NewsItem(**item) for item in dedupe_records(records)]

    def search(self, query: str, ticker: str | None = None, page_size: int = 10) -> list[NewsItem]:
        self.diagnostics = []
        if settings.use_mock_data:
            self._note("Mock data enabled; using mock news records.")
            return self._mock_results(query=query, ticker=ticker)
        if not settings.newsapi_key:
            self._note(f"NewsAPI key missing for {query}; trying RSS fallbacks.")
            return self._fallback_rss_results(query=query, ticker=ticker, page_size=page_size)

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
            self._note(f"NewsAPI failed for {query}: {exc}")
            return self._fallback_rss_results(query=query, ticker=ticker, page_size=page_size)

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
            self._note(f"NewsAPI returned {len(articles)} articles for {query}.")
            return articles

        self._note(f"NewsAPI returned no articles for {query}; trying RSS fallbacks.")
        return self._fallback_rss_results(query=query, ticker=ticker, page_size=page_size)

    def _fallback_rss_results(self, query: str, ticker: str | None, page_size: int) -> list[NewsItem]:
        yahoo_records = self._yahoo_finance_results(query=query, ticker=ticker, page_size=page_size)
        if yahoo_records:
            self._note(f"Yahoo Finance RSS returned {len(yahoo_records)} articles for {query}.")
            return yahoo_records

        google_records = self._google_news_results(query=query, ticker=ticker, page_size=page_size)
        if google_records:
            self._note(f"Google News RSS returned {len(google_records)} articles for {query}.")
            return google_records

        self._note(f"No live news found for {query} from NewsAPI, Yahoo Finance RSS, or Google News RSS.")
        return []

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
            self._note(f"Yahoo Finance RSS failed for {symbol}: {exc}")
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

    def _google_news_results(self, query: str, ticker: str | None, page_size: int) -> list[NewsItem]:
        search_query = f'"{query}" {ticker or ""} stock OR shares'
        params = {
            "q": search_query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        try:
            response = requests.get(self.google_rss_url, params=params, timeout=15)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError) as exc:
            self._note(f"Google News RSS failed for {query}: {exc}")
            return []

        records = []
        for item in root.findall(".//item"):
            title = self._clean_text(item.findtext("title", default="Untitled"))
            link = item.findtext("link", default="")
            description = self._clean_text(item.findtext("description", default=""))
            published_at = self._format_rss_date(item.findtext("pubDate", default=""))
            if not title or not link:
                continue
            records.append(
                {
                    "source": "Google News RSS",
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "content": description,
                    "ticker": ticker,
                    "company": query,
                    "source_type": "news",
                }
            )

        return [NewsItem(**item) for item in dedupe_records(records)[:page_size]]

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
