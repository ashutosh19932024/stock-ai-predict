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
    source_type: Literal["news", "official", "social", "conference"] = "news"


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


class PlannedTask(BaseModel):
    task: Literal[
        "single_stock_analysis",
        "market_screener",
        "watchlist_ranking",
        "event_drill_down",
        "backtest",
        "alert_setup",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class EventCluster(BaseModel):
    event_id: str
    ticker: str
    company: str
    headline: str
    summary: str
    sentiment: Literal["positive", "neutral", "negative"]
    weighted_score: float
    article_count: int
    sources: list[str]


class MarketSignal(BaseModel):
    ticker: str
    company: str
    market: Literal["US", "India"]
    cap_bucket: Literal["large", "mid", "small"]
    benchmark_symbol: str
    data_source: str
    gap_pct: float
    abnormal_volume: float
    realized_vol_20d: float
    beta_proxy: float
    benchmark_move_5d: float
    momentum_5d: float
    momentum_20d: float
    diagnostics: list[str] = Field(default_factory=list)


class AdvancedScreenResult(BaseModel):
    ticker: str
    company: str
    market: Literal["US", "India"]
    cap_bucket: Literal["large", "mid", "small"]
    overall_score: float
    tomorrow_up_probability: float = Field(ge=0.0, le=1.0)
    next_week_up_probability: float = Field(ge=0.0, le=1.0)
    expected_tomorrow_move_pct: float
    expected_week_move_pct: float
    recommendation: str
    reasons: list[str]
    top_events: list[EventCluster]
    diagnostics: list[str] = Field(default_factory=list)
