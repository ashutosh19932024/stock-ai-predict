from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from services.mock_data import MOCK_NEWS
from services.schemas import NewsItem
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class OfficialSourceService:
    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    def _note(self, message: str) -> None:
        self.diagnostics.append(message)
        logger.info(message)

    def fetch_company_updates(self, ticker: str) -> list[NewsItem]:
        """Fetch official company updates including press releases and conferences."""
        records = []

        # Mock data for development
        if settings.use_mock_data:
            mock_records = [item for item in MOCK_NEWS.get(ticker.upper(), []) if item.get("source_type") == "official"]
            records.extend([NewsItem(**item) for item in mock_records])

        # Try to fetch real NSE/BSE press releases
        if not settings.use_mock_data:
            try:
                nse_records = self._fetch_nse_press_releases(ticker)
                records.extend(nse_records)
            except Exception as exc:
                self._note(f"NSE press release fetch failed for {ticker}: {exc}")

            try:
                bse_records = self._fetch_bse_press_releases(ticker)
                records.extend(bse_records)
            except Exception as exc:
                self._note(f"BSE press release fetch failed for {ticker}: {exc}")

        return records

    def _fetch_nse_press_releases(self, ticker: str) -> list[NewsItem]:
        """Fetch press releases from NSE India."""
        # NSE press releases are typically available through their announcements API
        # This is a simplified implementation - in production you'd need proper NSE API access
        url = f"https://www.nseindia.com/api/corporate-announcements?symbol={ticker}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        records = []

        for announcement in data.get('data', [])[:5]:  # Limit to 5 most recent
            records.append(NewsItem(
                source="NSE India",
                title=announcement.get('subject', 'Press Release'),
                url=f"https://www.nseindia.com{announcement.get('attchmntFile', '')}",
                published_at=announcement.get('date', ''),
                content=announcement.get('desc', ''),
                ticker=ticker,
                company=announcement.get('symbol', ticker),
                source_type="official",
            ))

        return records

    def _fetch_bse_press_releases(self, ticker: str) -> list[NewsItem]:
        """Fetch press releases from BSE India."""
        # BSE press releases through their announcements page
        url = f"https://www.bseindia.com/corporates/ann.aspx"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        # For BSE, we'd typically need to search by company name or scrip code
        # This is a simplified implementation
        params = {
            'scripcode': ticker,
            'flag': 'announcements'
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        records = []

        # Parse BSE announcement table (simplified)
        announcement_rows = soup.find_all('tr', class_='announcement-row')[:5]

        for row in announcement_rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                records.append(NewsItem(
                    source="BSE India",
                    title=cols[1].get_text(strip=True),
                    url=f"https://www.bseindia.com{cols[1].find('a')['href']}" if cols[1].find('a') else "",
                    published_at=cols[0].get_text(strip=True),
                    content=cols[2].get_text(strip=True),
                    ticker=ticker,
                    company=ticker,
                    source_type="official",
                ))

        return records

    def fetch_press_conferences(self, ticker: str) -> list[NewsItem]:
        """Fetch press conference information for a company."""
        records = []

        if settings.use_mock_data:
            # Add mock press conference data
            mock_conferences = [
                {
                    "source": "Company IR",
                    "title": f"{ticker} Q4 2024 Earnings Press Conference",
                    "url": f"https://example.com/{ticker.lower()}-conference",
                    "published_at": "2024-04-15T10:00:00Z",
                    "content": f"Live press conference for {ticker} quarterly earnings discussion with analysts and investors.",
                    "ticker": ticker,
                    "company": ticker,
                    "source_type": "conference",
                }
            ]
            records.extend([NewsItem(**item) for item in mock_conferences])

        # In production, you could integrate with:
        # - Company investor relations websites
        # - Conference call transcripts
        # - Event calendars from Yahoo Finance, Seeking Alpha, etc.

        return records
