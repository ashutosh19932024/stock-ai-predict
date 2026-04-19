from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import requests

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

COMPANY_MAP = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "AMZN": "Amazon",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "RELIANCE": "Reliance Industries",
}

_ALIASES = {
    "APPLE": "AAPL",
    "TESLA": "TSLA",
    "NVIDIA": "NVDA",
    "MICROSOFT": "MSFT",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "META": "META",
    "FACEBOOK": "META",
    "AMAZON": "AMZN",
    "TATA CONSULTANCY SERVICES": "TCS",
    "TCS": "TCS",
    "TCS.NS": "TCS",
    "TCS.NSE": "TCS",
    "INFOSYS": "INFY",
    "INFY": "INFY",
    "INFY.NS": "INFY",
    "INFY.NSE": "INFY",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE": "RELIANCE",
    "RELIANCE.NS": "RELIANCE",
    "RELIANCE.NSE": "RELIANCE",
}


@dataclass(frozen=True, slots=True)
class ResolvedSecurity:
    ticker: str
    company: str
    region: str = ""
    matched_by: str = "fallback"


_HISTORICAL_SYMBOL_CANDIDATES = {
    "TCS": ["TCS.NS", "TCS.BO", "TCS"],
    "INFY": ["INFY.NS", "INFY.BO", "INFY"],
    "RELIANCE": ["RELIANCE.NS", "RELIANCE.BO", "RELIANCE"],
}


def _normalize_query(value: str) -> str:
    return " ".join((value or "").strip().split())


def _preferred_regions(query: str) -> set[str]:
    normalized = query.upper()
    if normalized.endswith(".NS") or normalized.endswith(".BO") or normalized.endswith(".BSE"):
        return {"India"}
    if " INDIA" in f" {normalized} " or " NSE" in f" {normalized} " or " BSE" in f" {normalized} ":
        return {"India"}
    if settings.default_market.upper() in {"IN", "INDIA"}:
        return {"India"}
    return {"United States", "Canada", "India"}


def _score_symbol_match(query: str, match: dict[str, str], preferred_regions: set[str]) -> float:
    symbol = (match.get("1. symbol") or "").upper()
    name = (match.get("2. name") or "").upper()
    asset_type = (match.get("3. type") or "").upper()
    region = match.get("4. region") or ""
    query_upper = query.upper()

    score = 0.0
    if asset_type == "EQUITY":
        score += 2.5
    if region in preferred_regions:
        score += 2.5
    if query_upper == symbol:
        score += 6.0
    if query_upper == name:
        score += 5.0
    if query_upper in symbol:
        score += 3.0
    if query_upper in name:
        score += 2.5
    if symbol.startswith(query_upper):
        score += 1.5
    if name.startswith(query_upper):
        score += 1.0
    if query_upper.endswith(".NS") and symbol.endswith(".NS"):
        score += 2.0
    if (query_upper.endswith(".BO") or query_upper.endswith(".BSE")) and (
        symbol.endswith(".BO") or symbol.endswith(".BSE")
    ):
        score += 2.0
    return score


@lru_cache(maxsize=256)
def _search_alpha_vantage(query: str) -> ResolvedSecurity | None:
    if settings.use_mock_data or not settings.alphavantage_api_key:
        return None

    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": query,
        "apikey": settings.alphavantage_api_key,
    }

    try:
        response = requests.get("https://www.alphavantage.co/query", params=params, timeout=20)
        response.raise_for_status()
        matches = response.json().get("bestMatches", [])
    except requests.RequestException as exc:
        logger.warning("Symbol search failed for %s: %s", query, exc)
        return None

    if not matches:
        return None

    preferred_regions = _preferred_regions(query)
    ranked_matches = sorted(
        matches,
        key=lambda item: _score_symbol_match(query, item, preferred_regions),
        reverse=True,
    )
    best = ranked_matches[0]
    symbol = (best.get("1. symbol") or query).upper()
    company = best.get("2. name") or symbol
    region = best.get("4. region") or ""
    return ResolvedSecurity(ticker=symbol, company=company, region=region, matched_by="alpha_vantage_search")


def resolve_security(query: str) -> ResolvedSecurity:
    normalized = _normalize_query(query)
    if not normalized:
        return ResolvedSecurity(ticker="UNKNOWN", company="UNKNOWN", matched_by="empty_input")

    upper_query = normalized.upper()

    local_ticker = _ALIASES.get(upper_query)
    if local_ticker:
        return ResolvedSecurity(
            ticker=local_ticker,
            company=COMPANY_MAP.get(local_ticker, local_ticker),
            matched_by="local_alias",
        )

    if upper_query in COMPANY_MAP:
        return ResolvedSecurity(ticker=upper_query, company=COMPANY_MAP[upper_query], matched_by="local_map")

    dynamic_match = _search_alpha_vantage(normalized)
    if dynamic_match:
        return dynamic_match

    return ResolvedSecurity(ticker=upper_query, company=normalized, matched_by="fallback_raw_input")


def resolve_company_name(ticker_or_query: str) -> str:
    return resolve_security(ticker_or_query).company


def get_historical_symbol_candidates(ticker: str) -> list[str]:
    normalized = (ticker or "").upper().strip()
    if not normalized:
        return []

    candidates = _HISTORICAL_SYMBOL_CANDIDATES.get(normalized, [normalized])

    # Normalize Indian exchange suffix variants across providers.
    if normalized.endswith(".BSE"):
        base = normalized[:-4]
        candidates = [f"{base}.BO", normalized, base, f"{base}.NS"] + candidates
    elif normalized.endswith(".BO"):
        base = normalized[:-3]
        candidates = [normalized, f"{base}.BSE", base, f"{base}.NS"] + candidates
    elif normalized.endswith(".NSE"):
        base = normalized[:-4]
        candidates = [f"{base}.NS", normalized, base, f"{base}.BO"] + candidates
    elif normalized.endswith(".NS"):
        base = normalized[:-3]
        candidates = [normalized, f"{base}.NSE", base, f"{base}.BO"] + candidates

    deduped = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped
