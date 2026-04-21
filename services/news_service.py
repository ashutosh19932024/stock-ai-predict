from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
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
from utils.runtime_context import get_active_market

logger = get_logger(__name__)


class NewsService:
    base_url = "https://newsapi.org/v2/everything"
    yahoo_rss_url = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    google_rss_url = "https://news.google.com/rss/search"
    nse_news_url = "https://www.nseindia.com/api/live-analysis"
    bse_news_url = "https://www.bseindia.com/markets/equity/EQReports/StockPrcHistori.aspx"
    max_news_age_days = 30

    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    def _note(self, message: str) -> None:
        self.diagnostics.append(message)
        logger.info(message)

    def _mock_results(self, query: str, ticker: str | None = None) -> list[NewsItem]:
        records = MOCK_NEWS.get((ticker or "").upper(), [])
        if not records and query:
            records = [item for items in MOCK_NEWS.values() for item in items if query.lower() in item["title"].lower()]
        items = [NewsItem(**item) for item in dedupe_records(records)]
        return self._filter_latest_news(items, label=f"mock:{ticker or query}")

    def search(self, query: str, ticker: str | None = None, page_size: int = 10) -> list[NewsItem]:
        self.diagnostics = []
        if settings.use_mock_data:
            self._note("Mock data enabled; using mock news records.")
            return self._mock_results(query=query, ticker=ticker)
        if not settings.newsapi_key:
            self._note(f"NewsAPI key missing for {query}; trying NSE/BSE and RSS fallbacks.")
            return self._fallback_with_exchanges(query=query, ticker=ticker, page_size=page_size)

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
            return self._fallback_with_exchanges(query=query, ticker=ticker, page_size=page_size)

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
        articles = self._filter_latest_news(articles, label=f"newsapi:{ticker or query}")
        if articles:
            self._note(f"NewsAPI returned {len(articles)} articles for {query}.")
            return articles

        self._note(f"NewsAPI returned no articles for {query}; trying NSE/BSE and RSS fallbacks.")
        return self._fallback_with_exchanges(query=query, ticker=ticker, page_size=page_size)

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

    def _fallback_with_exchanges(self, query: str, ticker: str | None, page_size: int) -> list[NewsItem]:
        """Try NSE/BSE news first, then RSS fallbacks."""
        all_records = []

        # Try NSE news for Indian stocks
        if ticker and self._is_indian_stock(ticker):
            try:
                nse_records = self._nse_news_results(query=query, ticker=ticker, page_size=page_size//2)
                all_records.extend(nse_records)
                self._note(f"NSE returned {len(nse_records)} articles for {ticker}.")
            except Exception as exc:
                self._note(f"NSE news fetch failed for {ticker}: {exc}")

            try:
                bse_records = self._bse_news_results(query=query, ticker=ticker, page_size=page_size//2)
                all_records.extend(bse_records)
                self._note(f"BSE returned {len(bse_records)} articles for {ticker}.")
            except Exception as exc:
                self._note(f"BSE news fetch failed for {ticker}: {exc}")

        # Add RSS fallbacks
        rss_records = self._fallback_rss_results(query=query, ticker=ticker, page_size=page_size)
        all_records.extend(rss_records)

        return all_records[:page_size]

    def _is_indian_stock(self, ticker: str) -> bool:
        """Check if ticker is likely an Indian stock."""
        ticker_upper = ticker.upper()
        return (
            ticker_upper.endswith('.NS') or
            ticker_upper.endswith('.BO') or
            ticker_upper.endswith('.NSE') or
            ticker_upper.endswith('.BSE') or
            ticker_upper in ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK'] or
            get_active_market() == "India"
        )

    def _nse_news_results(self, query: str, ticker: str, page_size: int) -> list[NewsItem]:
        """Fetch news from NSE India."""
        # NSE provides news through their live analysis API
        url = f"{self.nse_news_url}/news-analysis"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        params = {
            'symbol': ticker,
            'limit': page_size
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        records = []

        for item in data.get('data', [])[:page_size]:
            records.append(NewsItem(
                source="NSE India",
                title=item.get('headline', 'NSE News'),
                url=item.get('url', ''),
                published_at=item.get('date', ''),
                content=item.get('summary', ''),
                ticker=ticker,
                company=query,
                source_type="news",
            ))

        return records

    def _bse_news_results(self, query: str, ticker: str, page_size: int) -> list[NewsItem]:
        """Fetch news from BSE India."""
        # BSE news through their market data API
        url = "https://api.bseindia.com/BseIndiaAPI/api/GetNews/w"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        params = {
            'scripcode': ticker.replace('.BO', '').replace('.BSE', ''),
            'type': 'news',
            'limit': page_size
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        records = []

        for item in data.get('Table', [])[:page_size]:
            records.append(NewsItem(
                source="BSE India",
                title=item.get('Headline', 'BSE News'),
                url=item.get('NewsURL', ''),
                published_at=item.get('Date', ''),
                content=item.get('Summary', ''),
                ticker=ticker,
                company=query,
                source_type="news",
            ))

        return records

    def _yahoo_finance_results(self, query: str, ticker: str | None, page_size: int) -> list[NewsItem]:
        symbols = get_historical_symbol_candidates(ticker or query)
        if ticker and ticker.upper() not in symbols:
            symbols.append(ticker.upper())

        records: list[dict[str, str]] = []
        for symbol in symbols[:4]:
            records.extend(self._fetch_yahoo_rss_symbol(symbol=symbol, query=query, ticker=ticker))
            if len(records) >= page_size:
                break

        items = [NewsItem(**item) for item in dedupe_records(records)]
        return self._filter_latest_news(items, label=f"yahoo:{ticker or query}")[:page_size]

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
        active_market = get_active_market()
        params = {
            "q": search_query,
            "hl": "en-IN" if active_market == "India" else "en-US",
            "gl": "IN" if active_market == "India" else "US",
            "ceid": "IN:en" if active_market == "India" else "US:en",
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

        items = [NewsItem(**item) for item in dedupe_records(records)]
        return self._filter_latest_news(items, label=f"google:{ticker or query}")[:page_size]

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

    def _filter_latest_news(self, items: list[NewsItem], label: str) -> list[NewsItem]:
        if not items:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_news_age_days)
        fresh_items: list[tuple[datetime, NewsItem]] = []
        undated_items: list[NewsItem] = []

        for item in items:
            parsed_date = self._parse_datetime(item.published_at)
            if parsed_date is None:
                undated_items.append(item)
                continue
            if parsed_date >= cutoff:
                fresh_items.append((parsed_date, item))

        fresh_items.sort(key=lambda pair: pair[0], reverse=True)
        filtered = [item for _, item in fresh_items]

        if len(filtered) != len(items):
            self._note(
                f"Recency filter kept {len(filtered)} of {len(items)} items for {label} "
                f"(max age {self.max_news_age_days} days)."
            )

        if not filtered and undated_items:
            self._note(f"No recent dated items for {label}; keeping {len(undated_items)} undated items.")
            return undated_items

        return filtered

    def _parse_datetime(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
