from __future__ import annotations

import json
from typing import Any
from openai import OpenAI, OpenAIError
from utils.config import settings


class OpenAIService:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key)
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None

    def structured_sentiment(self, text: str, ticker: str, company: str) -> dict[str, Any] | None:
        if not self.client:
            return None

        schema = {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "company": {"type": "string"},
                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                "event_type": {"type": "string"},
                "impact_strength": {"type": "number", "minimum": 0, "maximum": 1},
                "horizon_days": {"type": "integer", "minimum": 1, "maximum": 30},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "summary": {"type": "string"},
            },
            "required": [
                "ticker",
                "company",
                "sentiment",
                "event_type",
                "impact_strength",
                "horizon_days",
                "confidence",
                "summary",
            ],
            "additionalProperties": False,
        }

        try:
            response = self.client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a financial news extraction assistant. "
                            "Return only structured JSON according to the schema. "
                            "Use impact_strength and confidence as decimal values between 0 and 1. "
                            "Do not give investment advice."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Ticker: {ticker}\nCompany: {company}\n"
                            f"Analyze this text for short-term market impact:\n{text}"
                        ),
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "news_sentiment",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            return json.loads(response.output_text)
        except OpenAIError as exc:
            print(f"OpenAI structured sentiment request failed: {exc}")
            return None

    def chat_summary(self, prompt: str) -> str:
        if not self.client:
            return "OpenAI API key missing. Running in rules-based mode."

        try:
            response = self.client.responses.create(
                model=settings.openai_model,
                input=prompt,
            )
            return response.output_text
        except OpenAIError as exc:
            print(f"OpenAI chat summary request failed: {exc}")
            return "OpenAI request failed. Running in fallback mode."
