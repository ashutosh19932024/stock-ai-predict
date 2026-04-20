from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    source: str
    title: str
    url: str
    published_at: str
    content: str
    ticker: str | None = None
    company: str | None = None
    source_type: Literal["news", "official", "social"] = "news"


class SentimentRecord(BaseModel):
    ticker: str
    company: str
    sentiment: Literal["positive", "neutral", "negative"]
    event_type: str = "general_news"
    impact_strength: float = Field(ge=0.0, le=1.0)
    horizon_days: int = Field(ge=1, le=30)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    source: str
    source_type: str
    published_at: str
    title: str
    url: str


class PriceSnapshot(BaseModel):
    ticker: str
    price: float
    prev_close: float
    daily_return: float
    volume: int
    avg_volume: int
    volatility_20d: float
    momentum_5d: float


class PredictionResult(BaseModel):
    ticker: str
    company: str
    outlook: Literal["bullish", "neutral", "bearish"]
    up_probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_move_pct: float
    drivers: list[str]
    risks: list[str]
    reasoning: str


class ChatAnswer(BaseModel):
    answer: str
    prediction: PredictionResult
    evidence: list[SentimentRecord]
    diagnostics: list[str] = Field(default_factory=list)
