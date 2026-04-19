from __future__ import annotations

from ml.feature_builder import FeatureBuilder
from ml.predict import Predictor
from services.market_data_service import MarketDataService
from services.schemas import PredictionResult, SentimentRecord


class PredictionAgent:
    def __init__(self) -> None:
        self.market_data = MarketDataService()
        self.feature_builder = FeatureBuilder()
        self.predictor = Predictor()

    def run(self, ticker: str, company: str, sentiments: list[SentimentRecord]) -> PredictionResult:
        price = self.market_data.get_snapshot(ticker)
        features = self.feature_builder.build(sentiments, price)
        return self.predictor.predict(ticker=ticker, company=company, features=features)
