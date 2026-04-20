from __future__ import annotations

import requests
from services.mock_data import MOCK_PRICES
from services.schemas import PriceSnapshot
from utils.config import settings


class MarketDataService:
    base_url = "https://www.alphavantage.co/query"

    def _mock_snapshot(self, ticker: str) -> PriceSnapshot:
        return PriceSnapshot(**MOCK_PRICES.get(ticker.upper(), {
            "ticker": ticker.upper(),
            "price": 100.0,
            "prev_close": 99.0,
            "daily_return": 0.01,
            "volume": 1000000,
            "avg_volume": 900000,
            "volatility_20d": 0.02,
            "momentum_5d": 0.01,
        }))

    def _neutral_snapshot(self, ticker: str) -> PriceSnapshot:
        return PriceSnapshot(
            ticker=ticker.upper(),
            price=0.0,
            prev_close=0.0,
            daily_return=0.0,
            volume=0,
            avg_volume=1,
            volatility_20d=0.0,
            momentum_5d=0.0,
        )

    def get_snapshot(self, ticker: str) -> PriceSnapshot:
        if settings.use_mock_data:
            return self._mock_snapshot(ticker)
        if not settings.alphavantage_api_key:
            return self._neutral_snapshot(ticker)

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.upper(),
            "apikey": settings.alphavantage_api_key,
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json().get("Global Quote", {})
        except requests.RequestException:
            return self._neutral_snapshot(ticker)

        price = float(payload.get("05. price", 0.0) or 0.0)
        prev_close = float(payload.get("08. previous close", 0.0) or 0.0)
        volume = int(float(payload.get("06. volume", 0) or 0))
        daily_return = (price - prev_close) / prev_close if prev_close else 0.0

        if price <= 0 or prev_close < 0:
            return self._neutral_snapshot(ticker)

        return PriceSnapshot(
            ticker=ticker.upper(),
            price=price,
            prev_close=prev_close,
            daily_return=daily_return,
            volume=volume,
            avg_volume=volume,
            volatility_20d=0.02,
            momentum_5d=daily_return,
        )
