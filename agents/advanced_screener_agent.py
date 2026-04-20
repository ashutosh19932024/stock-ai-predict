from __future__ import annotations

from agents.event_extraction_agent import EventExtractionAgent, SOURCE_WEIGHTS, SENTIMENT_SIGN
from agents.filings_agent import FilingsAgent
from agents.market_data_agent import MarketDataAgent
from agents.news_agent import NewsAgent
from agents.prediction_agent import PredictionAgent
from agents.sentiment_agent import SentimentAgent
from agents.social_agent import SocialAgent
from ml.weekly_forecast import WeeklyForecastModel
from services.historical_data_service import HistoricalMarketDataService
from services.schemas import AdvancedScreenResult, SentimentRecord
from services.universe_service import CapBucket, UniverseMarket, get_universe
from utils.helpers import clamp


class AdvancedScreenerAgent:
    def __init__(self) -> None:
        self.news_agent = NewsAgent()
        self.filings_agent = FilingsAgent()
        self.social_agent = SocialAgent()
        self.sentiment_agent = SentimentAgent()
        self.prediction_agent = PredictionAgent()
        self.event_agent = EventExtractionAgent()
        self.market_agent = MarketDataAgent()
        self.history_service = HistoricalMarketDataService()

    def rank(
        self,
        markets: list[UniverseMarket],
        cap_buckets: list[CapBucket],
        top_n: int = 10,
    ) -> list[AdvancedScreenResult]:
        candidates = get_universe(markets=markets, cap_buckets=cap_buckets)
        results: list[AdvancedScreenResult] = []

        for candidate in candidates:
            ticker = candidate["ticker"]
            company = candidate["company"]
            market = candidate["market"]
            cap_bucket = candidate["cap_bucket"]

            records = []
            records.extend(self.news_agent.collect(ticker=ticker, company=company))
            records.extend(self.filings_agent.collect(ticker))
            records.extend(self.social_agent.collect(ticker=ticker, company=company))
            sentiments = [self.sentiment_agent.analyze(item) for item in records]

            prediction = self.prediction_agent.run(ticker=ticker, company=company, sentiments=sentiments)
            market_signal = self.market_agent.analyze(ticker=ticker, company=company, market=market, cap_bucket=cap_bucket)
            history_result = self.history_service.get_daily_history(ticker, years=5)

            tomorrow_prob = prediction.up_probability
            next_week_prob = prediction.up_probability
            tomorrow_move = prediction.expected_move_pct
            next_week_move = prediction.expected_move_pct
            recommendation = "Hold / Wait For Confirmation"
            recommendation_reason = "The combined signal is not yet strong enough."
            diagnostics = list(self.news_agent.diagnostics) + list(market_signal.diagnostics) + list(history_result.diagnostics)

            if len(history_result.data) >= 260:
                try:
                    forecast = WeeklyForecastModel().run(history_result.data)
                    tomorrow_prob = forecast.tomorrow.probability_up
                    next_week_prob = forecast.next_week.probability_up
                    tomorrow_move = forecast.tomorrow.predicted_return_pct
                    next_week_move = forecast.next_week.predicted_return_pct
                    recommendation = forecast.final_recommendation
                    recommendation_reason = forecast.recommendation_reason
                except ValueError as exc:
                    diagnostics.append(str(exc))

            event_clusters = self.event_agent.extract(ticker=ticker, company=company, evidence=sentiments)
            news_score = self._news_score(sentiments)
            market_score = self._market_score(market_signal)
            ml_score = ((tomorrow_prob - 0.5) * 2 * 0.45) + ((next_week_prob - 0.5) * 2 * 0.55)
            overall_score = news_score * 0.45 + market_score * 0.25 + ml_score * 0.30

            reasons = []
            if news_score > 0.1:
                reasons.append("News and event tone is net positive after source weighting.")
            if market_signal.momentum_5d > 0:
                reasons.append("Recent momentum is supportive.")
            if market_signal.abnormal_volume > 1.1:
                reasons.append("Volume is above normal, suggesting stronger participation.")
            if tomorrow_prob > 0.58:
                reasons.append("Tomorrow model probability leans upward.")
            if next_week_prob > 0.58:
                reasons.append("Next-week model also supports upside.")
            if not reasons:
                reasons.append("The signal is ranked mainly on relative strength versus the selected universe.")

            results.append(
                AdvancedScreenResult(
                    ticker=ticker,
                    company=company,
                    market=market,
                    cap_bucket=cap_bucket,
                    overall_score=float(overall_score),
                    tomorrow_up_probability=clamp(tomorrow_prob, 0.0, 1.0),
                    next_week_up_probability=clamp(next_week_prob, 0.0, 1.0),
                    expected_tomorrow_move_pct=float(tomorrow_move),
                    expected_week_move_pct=float(next_week_move),
                    recommendation=f"{recommendation}: {recommendation_reason}",
                    reasons=reasons,
                    top_events=event_clusters[:3],
                    diagnostics=diagnostics[:12],
                )
            )

        return sorted(
            results,
            key=lambda item: (item.overall_score, item.tomorrow_up_probability, item.next_week_up_probability),
            reverse=True,
        )[:top_n]

    def _news_score(self, sentiments: list[SentimentRecord]) -> float:
        if not sentiments:
            return 0.0
        total = 0.0
        for item in sentiments:
            total += (
                SENTIMENT_SIGN.get(item.sentiment, 0.0)
                * item.impact_strength
                * item.confidence
                * SOURCE_WEIGHTS.get(item.source_type, 0.5)
            )
        return total / max(len(sentiments), 1)

    def _market_score(self, signal) -> float:
        return (
            signal.momentum_5d * 2.2
            + signal.momentum_20d * 1.3
            + (signal.abnormal_volume - 1.0) * 0.25
            - signal.realized_vol_20d * 1.8
            - signal.beta_proxy * 0.03
            - signal.benchmark_move_5d * 0.2
        )
