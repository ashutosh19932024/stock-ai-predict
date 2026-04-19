from __future__ import annotations

from services.openai_service import OpenAIService
from services.schemas import PredictionResult, SentimentRecord


class ExplanationAgent:
    def __init__(self) -> None:
        self.openai = OpenAIService()

    def generate(self, prediction: PredictionResult, evidence: list[SentimentRecord]) -> str:
        top_titles = "\n".join(f"- {item.title} ({item.sentiment})" for item in evidence[:5])
        prompt = f"""
Create a concise analyst-style summary.

Ticker: {prediction.ticker}
Company: {prediction.company}
Outlook: {prediction.outlook}
Up probability: {prediction.up_probability:.2f}
Confidence: {prediction.confidence:.2f}
Expected move %: {prediction.expected_move_pct}
Drivers: {prediction.drivers}
Risks: {prediction.risks}
Evidence:\n{top_titles}

Return 1 short paragraph and 3 bullet-style lines separated by newlines.
"""
        result = self.openai.chat_summary(prompt)
        if result.startswith("OpenAI"):
            return (
                f"{prediction.company} shows a {prediction.outlook} near-term setup with {prediction.up_probability:.0%} up probability.\n"
                f"Driver: {prediction.drivers[0]}\n"
                f"Risk: {prediction.risks[0]}\n"
                f"Expected move: {prediction.expected_move_pct}%"
            )
        return result
