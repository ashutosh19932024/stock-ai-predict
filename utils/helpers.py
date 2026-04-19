from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def safe_mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
