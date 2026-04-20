from __future__ import annotations

from agents.explanation_agent import ExplanationAgent
from agents.news_agent import NewsAgent
from agents.prediction_agent import PredictionAgent
from agents.sentiment_agent import SentimentAgent
from services.company_service import resolve_security
from services.schemas import ChatAnswer


class StockAnalysisOrchestrator:
    def __init__(self) -> None:
        self.news_agent = NewsAgent()
        self.sentiment_agent = SentimentAgent()
        self.prediction_agent = PredictionAgent()
        self.explanation_agent = ExplanationAgent()

    def run(self, identifier: str) -> ChatAnswer:
        resolved = resolve_security(identifier)
        news_items = self.news_agent.collect(ticker=resolved.ticker, company=resolved.company)
        sentiments = [self.sentiment_agent.analyze(item) for item in news_items]
        prediction = self.prediction_agent.run(
            ticker=resolved.ticker,
            company=resolved.company,
            sentiments=sentiments,
        )
        answer = self.explanation_agent.generate(prediction=prediction, evidence=sentiments)
        return ChatAnswer(
            answer=answer,
            prediction=prediction,
            evidence=sentiments,
            diagnostics=self.news_agent.diagnostics,
        )
