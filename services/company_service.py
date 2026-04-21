from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import requests

from services.universe_service import UNIVERSE, get_universe
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Minimal essential mappings for common variations
COMPANY_MAP = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "AMZN": "Amazon",
}

# Essential aliases for common variations
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
}


@dataclass(frozen=True, slots=True)
class ResolvedSecurity:
    ticker: str
    company: str
    region: str = ""
    matched_by: str = "fallback"


_HISTORICAL_SYMBOL_CANDIDATES = {
    # Will be populated dynamically from universe
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

    # Check local aliases first
    local_ticker = _ALIASES.get(upper_query)
    if local_ticker:
        return ResolvedSecurity(
            ticker=local_ticker,
            company=COMPANY_MAP.get(local_ticker, local_ticker),
            matched_by="local_alias",
        )

    # Check local company map
    if upper_query in COMPANY_MAP:
        return ResolvedSecurity(ticker=upper_query, company=COMPANY_MAP[upper_query], matched_by="local_map")

    # Search universe for any market/cap combination
    for market in UNIVERSE:
        for cap_bucket in UNIVERSE[market]:
            for stock in UNIVERSE[market][cap_bucket]:
                ticker = stock["ticker"].upper()
                company = stock["company"]
                
                # Match by ticker
                if upper_query == ticker:
                    return ResolvedSecurity(
                        ticker=ticker, 
                        company=company, 
                        region=market, 
                        matched_by="universe_ticker"
                    )
                
                # Match by company name (case insensitive)
                if upper_query == company.upper():
                    return ResolvedSecurity(
                        ticker=ticker, 
                        company=company, 
                        region=market, 
                        matched_by="universe_company"
                    )
                
                # Match by ticker without suffix (.NS, .BO, etc.)
                if upper_query == ticker.split('.')[0]:
                    return ResolvedSecurity(
                        ticker=ticker, 
                        company=company, 
                        region=market, 
                        matched_by="universe_ticker_base"
                    )

    # Try Alpha Vantage API for dynamic lookup
    dynamic_match = _search_alpha_vantage(normalized)
    if dynamic_match:
        return dynamic_match

    # Final fallback - use query as ticker, try to make it look like a company name
    company_name = normalized.replace('.', ' ').replace('_', ' ').title()
    return ResolvedSecurity(ticker=upper_query, company=company_name, matched_by="fallback_raw_input")


def resolve_company_name(ticker_or_query: str) -> str:
    return resolve_security(ticker_or_query).company


def get_historical_symbol_candidates(ticker: str) -> list[str]:
    normalized = (ticker or "").upper().strip()
    if not normalized:
        return []

    candidates = [normalized]

    # Check if ticker exists in universe and add variations
    for market in UNIVERSE:
        for cap_bucket in UNIVERSE[market]:
            for stock in UNIVERSE[market][cap_bucket]:
                universe_ticker = stock["ticker"].upper()
                if normalized == universe_ticker or normalized == universe_ticker.split('.')[0]:
                    # Add the full universe ticker
                    if universe_ticker not in candidates:
                        candidates.append(universe_ticker)
                    
                    # For Indian stocks, add exchange variations
                    if market == "India" and '.' not in universe_ticker:
                        candidates.extend([
                            f"{universe_ticker}.NS",
                            f"{universe_ticker}.BO", 
                            f"{universe_ticker}.NSE",
                            f"{universe_ticker}.BSE"
                        ])

    # Normalize Indian exchange suffix variants across providers
    if normalized.endswith(".BSE"):
        base = normalized[:-4]
        candidates.extend([f"{base}.BO", normalized, base, f"{base}.NS"])
    elif normalized.endswith(".BO"):
        base = normalized[:-3]
        candidates.extend([normalized, f"{base}.BSE", base, f"{base}.NS"])
    elif normalized.endswith(".NSE"):
        base = normalized[:-4]
        candidates.extend([f"{base}.NS", normalized, base, f"{base}.BO"])
    elif normalized.endswith(".NS"):
        base = normalized[:-3]
        candidates.extend([normalized, f"{base}.NSE", base, f"{base}.BO"])

    # Remove duplicates while preserving order
    deduped = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    
    return deduped
