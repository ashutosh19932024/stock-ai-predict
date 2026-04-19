from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from services.company_service import get_historical_symbol_candidates
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HistoricalDataResult:
    ticker: str
    data: pd.DataFrame
    source: str
    is_live: bool
    provider_symbol: str = ""
    diagnostics: tuple[str, ...] = ()


class HistoricalMarketDataService:
    base_url = "https://www.alphavantage.co/query"

    def get_daily_history(self, ticker: str, years: int = 10) -> HistoricalDataResult:
        ticker = ticker.upper().strip()
        if settings.use_mock_data or not settings.alphavantage_api_key:
            return HistoricalDataResult(
                ticker=ticker,
                data=self._generate_mock_history(ticker=ticker, years=years),
                source="synthetic_mock_data",
                is_live=False,
                provider_symbol=ticker,
                diagnostics=("Mock mode is enabled or Alpha Vantage key is missing.",),
            )
        diagnostics: list[str] = []
        for candidate in get_historical_symbol_candidates(ticker):
            live_result, alpha_note = self._fetch_alpha_vantage_history(
                request_ticker=ticker,
                provider_symbol=candidate,
                years=years,
            )
            diagnostics.append(alpha_note)
            if live_result:
                return live_result

            yahoo_result, yahoo_note = self._fetch_yfinance_history(
                request_ticker=ticker,
                provider_symbol=candidate,
                years=years,
            )
            diagnostics.append(yahoo_note)
            if yahoo_result:
                return yahoo_result

        logger.warning("Historical price request failed for %s across all live providers; using synthetic fallback.", ticker)
        return HistoricalDataResult(
            ticker=ticker,
            data=self._generate_mock_history(ticker=ticker, years=years),
            source="synthetic_mock_fallback",
            is_live=False,
            provider_symbol=ticker,
            diagnostics=tuple(diagnostics),
        )

    def _fetch_alpha_vantage_history(
        self,
        request_ticker: str,
        provider_symbol: str,
        years: int,
    ) -> tuple[HistoricalDataResult | None, str]:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": provider_symbol,
            "outputsize": "full",
            "apikey": settings.alphavantage_api_key,
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            series = payload.get("Time Series (Daily)", {})
            if not series:
                return None, f"Alpha Vantage {provider_symbol}: no daily history returned."
            frame = self._parse_alpha_vantage_history(series)
            cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.DateOffset(years=years)
            frame = frame[frame.index >= cutoff].copy()
            if frame.empty:
                return None, f"Alpha Vantage {provider_symbol}: history empty after {years}-year filter."
            return (
                HistoricalDataResult(
                    ticker=request_ticker,
                    data=frame,
                    source="alpha_vantage_daily_adjusted",
                    is_live=True,
                    provider_symbol=provider_symbol,
                    diagnostics=(f"Alpha Vantage {provider_symbol}: success.",),
                ),
                f"Alpha Vantage {provider_symbol}: success.",
            )
        except (requests.RequestException, ValueError, KeyError) as exc:
            return None, f"Alpha Vantage {provider_symbol}: {exc}"

    def _fetch_yfinance_history(
        self,
        request_ticker: str,
        provider_symbol: str,
        years: int,
    ) -> tuple[HistoricalDataResult | None, str]:
        try:
            import yfinance as yf
        except ImportError:
            return None, "yfinance is not installed."

        try:
            history = yf.Ticker(provider_symbol).history(period=f"{years}y", interval="1d", auto_adjust=False)
            if history.empty:
                return None, f"yfinance {provider_symbol}: empty history."
            frame = history.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )[["open", "high", "low", "close", "volume"]].copy()
            frame.index = pd.to_datetime(frame.index).tz_localize(None)
            frame.index.name = "date"
            frame = frame[(frame["close"] > 0) & (frame["volume"] >= 0)].copy()
            if frame.empty:
                return None, f"yfinance {provider_symbol}: history invalid after cleanup."
            return (
                HistoricalDataResult(
                    ticker=request_ticker,
                    data=frame,
                    source="yfinance_history",
                    is_live=True,
                    provider_symbol=provider_symbol,
                    diagnostics=(f"yfinance {provider_symbol}: success.",),
                ),
                f"yfinance {provider_symbol}: success.",
            )
        except Exception as exc:
            return None, f"yfinance {provider_symbol}: {exc}"

    def _parse_alpha_vantage_history(self, series: dict[str, dict[str, str]]) -> pd.DataFrame:
        rows = []
        for date_str, values in series.items():
            rows.append(
                {
                    "date": pd.to_datetime(date_str),
                    "open": float(values.get("1. open", 0.0) or 0.0),
                    "high": float(values.get("2. high", 0.0) or 0.0),
                    "low": float(values.get("3. low", 0.0) or 0.0),
                    "close": float(values.get("5. adjusted close", values.get("4. close", 0.0)) or 0.0),
                    "volume": float(values.get("6. volume", 0.0) or 0.0),
                }
            )

        frame = pd.DataFrame(rows).sort_values("date").set_index("date")
        frame = frame[(frame["close"] > 0) & (frame["volume"] >= 0)].copy()
        return frame

    def _generate_mock_history(self, ticker: str, years: int) -> pd.DataFrame:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=365 * years)
        index = pd.bdate_range(start=start_date, end=end_date)

        seed = sum(ord(char) for char in ticker) % 10_000
        rng = np.random.default_rng(seed)

        market_drift = rng.uniform(0.0001, 0.0007)
        market_vol = rng.uniform(0.008, 0.025)
        shocks = rng.normal(loc=market_drift, scale=market_vol, size=len(index))
        close = 100 * np.exp(np.cumsum(shocks))

        open_price = close * (1 + rng.normal(0, 0.0035, size=len(index)))
        high = np.maximum(open_price, close) * (1 + rng.uniform(0.001, 0.015, size=len(index)))
        low = np.minimum(open_price, close) * (1 - rng.uniform(0.001, 0.015, size=len(index)))
        volume = rng.integers(800_000, 9_000_000, size=len(index)).astype(float)

        frame = pd.DataFrame(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
            index=index,
        )
        frame.index.name = "date"
        return frame.round(2)
