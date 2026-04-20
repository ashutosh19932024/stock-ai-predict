from __future__ import annotations

from services.schemas import PlannedTask


class PlannerAgent:
    def plan(self, prompt: str) -> PlannedTask:
        text = (prompt or "").lower()

        if any(token in text for token in ["screen", "screener", "top 10", "large cap", "mid cap", "small cap"]):
            return PlannedTask(
                task="market_screener",
                confidence=0.9,
                rationale="The prompt asks for a ranked stock screen across market-cap buckets and regions.",
            )
        if "watchlist" in text and any(token in text for token in ["rank", "ranking", "best"]):
            return PlannedTask(
                task="watchlist_ranking",
                confidence=0.86,
                rationale="The prompt asks to rank an existing watchlist.",
            )
        if any(token in text for token in ["filing", "press release", "event", "drill"]):
            return PlannedTask(
                task="event_drill_down",
                confidence=0.78,
                rationale="The prompt asks for deeper event-level inspection.",
            )
        if "backtest" in text:
            return PlannedTask(task="backtest", confidence=0.95, rationale="The prompt explicitly asks for backtesting.")
        if "alert" in text:
            return PlannedTask(task="alert_setup", confidence=0.95, rationale="The prompt asks for alert behavior.")
        return PlannedTask(
            task="single_stock_analysis",
            confidence=0.72,
            rationale="The prompt appears to be about a single stock or general stock analysis.",
        )
