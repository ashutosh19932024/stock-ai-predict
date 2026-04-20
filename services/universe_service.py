from __future__ import annotations

from typing import Literal


UniverseMarket = Literal["US", "India"]
CapBucket = Literal["large", "mid", "small"]


UNIVERSE: dict[UniverseMarket, dict[CapBucket, list[dict[str, str]]]] = {
    "US": {
        "large": [
            {"ticker": "AAPL", "company": "Apple"},
            {"ticker": "MSFT", "company": "Microsoft"},
            {"ticker": "NVDA", "company": "NVIDIA"},
            {"ticker": "AMZN", "company": "Amazon"},
            {"ticker": "GOOGL", "company": "Alphabet"},
            {"ticker": "META", "company": "Meta"},
            {"ticker": "TSLA", "company": "Tesla"},
            {"ticker": "AVGO", "company": "Broadcom"},
            {"ticker": "JPM", "company": "JPMorgan Chase"},
            {"ticker": "WMT", "company": "Walmart"},
        ],
        "mid": [
            {"ticker": "UBER", "company": "Uber"},
            {"ticker": "PLTR", "company": "Palantir"},
            {"ticker": "CRWD", "company": "CrowdStrike"},
            {"ticker": "SNOW", "company": "Snowflake"},
            {"ticker": "DDOG", "company": "Datadog"},
            {"ticker": "NET", "company": "Cloudflare"},
            {"ticker": "HOOD", "company": "Robinhood"},
            {"ticker": "COIN", "company": "Coinbase"},
            {"ticker": "TTD", "company": "Trade Desk"},
            {"ticker": "RBLX", "company": "Roblox"},
        ],
        "small": [
            {"ticker": "SOUN", "company": "SoundHound AI"},
            {"ticker": "RKLB", "company": "Rocket Lab"},
            {"ticker": "IOT", "company": "Samsara"},
            {"ticker": "ASTS", "company": "AST SpaceMobile"},
            {"ticker": "UPST", "company": "Upstart"},
            {"ticker": "RUN", "company": "Sunrun"},
            {"ticker": "SOFI", "company": "SoFi"},
            {"ticker": "ACHR", "company": "Archer Aviation"},
            {"ticker": "IONQ", "company": "IonQ"},
            {"ticker": "CLOV", "company": "Clover Health"},
        ],
    },
    "India": {
        "large": [
            {"ticker": "RELIANCE", "company": "Reliance Industries"},
            {"ticker": "TCS", "company": "Tata Consultancy Services"},
            {"ticker": "INFY", "company": "Infosys"},
            {"ticker": "HDFCBANK.NS", "company": "HDFC Bank"},
            {"ticker": "ICICIBANK.NS", "company": "ICICI Bank"},
            {"ticker": "BHARTIARTL.NS", "company": "Bharti Airtel"},
            {"ticker": "LT.NS", "company": "Larsen & Toubro"},
            {"ticker": "SBIN.NS", "company": "State Bank of India"},
            {"ticker": "ITC.NS", "company": "ITC"},
            {"ticker": "HINDUNILVR.NS", "company": "Hindustan Unilever"},
        ],
        "mid": [
            {"ticker": "TRENT.NS", "company": "Trent"},
            {"ticker": "DIXON.NS", "company": "Dixon Technologies"},
            {"ticker": "BSE.NS", "company": "BSE"},
            {"ticker": "PERSISTENT.NS", "company": "Persistent Systems"},
            {"ticker": "COFORGE.NS", "company": "Coforge"},
            {"ticker": "ADANIGREEN.NS", "company": "Adani Green Energy"},
            {"ticker": "MPHASIS.NS", "company": "Mphasis"},
            {"ticker": "AUBANK.NS", "company": "AU Small Finance Bank"},
            {"ticker": "MAXHEALTH.NS", "company": "Max Healthcare"},
            {"ticker": "LTIM.NS", "company": "LTIMindtree"},
        ],
        "small": [
            {"ticker": "IREDA.NS", "company": "Indian Renewable Energy Development Agency"},
            {"ticker": "IRFC.NS", "company": "Indian Railway Finance Corp"},
            {"ticker": "CDSL.NS", "company": "Central Depository Services"},
            {"ticker": "ANGELONE.NS", "company": "Angel One"},
            {"ticker": "BLS.NS", "company": "BLS International"},
            {"ticker": "KAYNES.NS", "company": "Kaynes Technology"},
            {"ticker": "CLEAN.NS", "company": "Clean Science and Technology"},
            {"ticker": "CAMPUS.NS", "company": "Campus Activewear"},
            {"ticker": "LATENTVIEW.NS", "company": "Latent View Analytics"},
            {"ticker": "MEDPLUS.NS", "company": "MedPlus Health Services"},
        ],
    },
}


def get_universe(markets: list[UniverseMarket], cap_buckets: list[CapBucket]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for market in markets:
        for cap_bucket in cap_buckets:
            for item in UNIVERSE.get(market, {}).get(cap_bucket, []):
                key = f"{market}:{cap_bucket}:{item['ticker']}"
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "ticker": item["ticker"],
                        "company": item["company"],
                        "market": market,
                        "cap_bucket": cap_bucket,
                    }
                )
    return records
