from __future__ import annotations

import pandas as pd

from services.historical_data_service import HistoricalMarketDataService
from services.schemas import MarketSignal
from services.universe_service import CapBucket, UniverseMarket
from utils.helpers import clamp


class MarketDataAgent:
    benchmark_map = {
        "US": "SPY",
        "India": "NIFTYBEES.NS",
    }

    def __init__(self) -> None:
        self.history_service = HistoricalMarketDataService()

    def analyze(self, ticker: str, company: str, market: UniverseMarket, cap_bucket: CapBucket) -> MarketSignal:
        benchmark_symbol = self.benchmark_map[market]
        history_result = self.history_service.get_daily_history(ticker, years=3)
        benchmark_result = self.history_service.get_daily_history(benchmark_symbol, years=3)

        diagnostics = list(history_result.diagnostics)
        if benchmark_result.diagnostics:
            diagnostics.extend(list(benchmark_result.diagnostics))

        stock = history_result.data.sort_index().copy()
        benchmark = benchmark_result.data.sort_index().copy()

        if len(stock) < 25:
            return MarketSignal(
                ticker=ticker,
                company=company,
                market=market,
                cap_bucket=cap_bucket,
                benchmark_symbol=benchmark_symbol,
                data_source=history_result.source,
                gap_pct=0.0,
                abnormal_volume=1.0,
                realized_vol_20d=0.0,
                beta_proxy=1.0,
                benchmark_move_5d=0.0,
                momentum_5d=0.0,
                momentum_20d=0.0,
                diagnostics=diagnostics + ["Insufficient historical rows for market signal calculation."],
            )

        stock["return_1d"] = stock["close"].pct_change()
        stock["momentum_5d"] = stock["close"].pct_change(5)
        stock["momentum_20d"] = stock["close"].pct_change(20)
        stock["realized_vol_20d"] = stock["return_1d"].rolling(20).std()
        stock["avg_volume_20d"] = stock["volume"].rolling(20).mean()
        last = stock.iloc[-1]

        gap_pct = ((last["open"] - stock["close"].iloc[-2]) / stock["close"].iloc[-2]) if len(stock) > 1 else 0.0
        abnormal_volume = (last["volume"] / last["avg_volume_20d"]) if last["avg_volume_20d"] else 1.0

        benchmark_move_5d = 0.0
        beta_proxy = 1.0
        if len(benchmark) >= 25:
            benchmark["return_1d"] = benchmark["close"].pct_change()
            benchmark_move_5d = float(benchmark["close"].pct_change(5).iloc[-1])
            benchmark_vol = float(benchmark["return_1d"].rolling(20).std().iloc[-1] or 0.0)
            stock_vol = float(last["realized_vol_20d"] or 0.0)
            beta_proxy = stock_vol / benchmark_vol if benchmark_vol else 1.0

        return MarketSignal(
            ticker=ticker,
            company=company,
            market=market,
            cap_bucket=cap_bucket,
            benchmark_symbol=benchmark_symbol,
            data_source=history_result.source,
            gap_pct=float(gap_pct),
            abnormal_volume=float(abnormal_volume),
            realized_vol_20d=float(last["realized_vol_20d"] or 0.0),
            beta_proxy=float(clamp(beta_proxy, 0.2, 3.0)),
            benchmark_move_5d=float(benchmark_move_5d),
            momentum_5d=float(last["momentum_5d"] or 0.0),
            momentum_20d=float(last["momentum_20d"] or 0.0),
            diagnostics=diagnostics,
        )
