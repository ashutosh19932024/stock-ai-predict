from __future__ import annotations

import streamlit as st
from agents.orchestrator import StockAnalysisOrchestrator
from services.company_service import COMPANY_MAP, resolve_security
from utils.config import settings
from utils.runtime_context import get_active_market


def is_live_source_url(url: str) -> bool:
    normalized = (url or "").strip().lower()
    return bool(normalized) and "example.com" not in normalized


def generate_detailed_analysis(prediction, evidence):
    """Generate detailed purchase recommendation analysis."""
    outlook = prediction.outlook
    up_prob = prediction.up_probability
    confidence = prediction.confidence
    expected_move = prediction.expected_move_pct
    
    analysis = []
    
    if outlook == "bullish" and confidence >= 0.6 and expected_move > 0.5:
        recommendation = "**Consider purchasing tomorrow**"
        analysis.append("### Why Purchase?")
        analysis.append(f"- **Strong Confidence ({confidence:.0%})**: Reliable signal with high certainty")
        analysis.append(f"- **Good Expected Move ({expected_move:.2f}%)**: Meaningful potential impact")
        analysis.append(f"- **Favorable Up Probability ({up_prob:.0%})**: Clear bullish momentum")

        analysis.append("\n### Positive Factors:")
        analysis.append("**Technical Analysis:**")
        analysis.append("- Strong momentum indicators")
        analysis.append("- Clear directional trend")
        analysis.append("- Bullish sentiment dominance")

        analysis.append("\n**Supporting Evidence:**")
        positive_evidence = [e for e in evidence if e.sentiment == "positive"]
        if positive_evidence:
            for e in positive_evidence[:3]:
                analysis.append(f"- {e.title} (positive impact: {e.impact_strength:.2f})")
    elif outlook == "bearish":
        recommendation = "**Avoid purchasing tomorrow**"
        analysis.append("### Why Avoid Buying?")
        analysis.append(f"- **Low Up Probability ({up_prob:.0%})**: The setup favors downside rather than upside.")
        analysis.append(f"- **Expected Move ({expected_move:.2f}%)**: The projected move is negative.")
        analysis.append(f"- **Confidence ({confidence:.0%})**: The model has meaningful conviction in the bearish setup.")

        analysis.append("\n### Negative Factors:")
        analysis.append("**Technical Analysis Concerns:**")
        analysis.append("- Momentum is weak or deteriorating")
        analysis.append("- News and price action are not aligned for upside")
        analysis.append("- Risk/reward is unfavorable for a fresh buy")

        analysis.append("\n**Supporting Evidence:**")
        negative_evidence = [e for e in evidence if e.sentiment == "negative"]
        if negative_evidence:
            for e in negative_evidence[:3]:
                analysis.append(f"- {e.title} (negative impact: {e.impact_strength:.2f})")
    else:
        recommendation = "**Wait for a clearer setup**"
        analysis.append("### Why Wait?")
        analysis.append(f"- **Mixed Probability ({up_prob:.0%})**: The directional edge is not strong enough.")
        analysis.append(f"- **Confidence ({confidence:.0%})**: Evidence is not decisive.")
        analysis.append(f"- **Expected Move ({expected_move:.2f}%)**: The potential move is modest.")

        analysis.append("\n### Current Read:")
        analysis.append("- Signals are mixed between sentiment and price action")
        analysis.append("- Better confirmation may come from fresh news or a stronger trend")
        analysis.append("- Patience may offer a better entry than forcing a trade")
    
    return f"## Purchase Recommendation\n\n{recommendation}\n\n" + "\n".join(analysis)


def build_source_section(evidence):
    if not evidence:
        return "_No source evidence available._"

    lines = []
    for item in evidence[:5]:
        link_text = (
            f"[Open source]({item.url})"
            if is_live_source_url(item.url)
            else "No live article link available in demo mode"
        )
        lines.append(
            f"- {item.title} | {item.source} | {item.source_type} | {item.sentiment} | impact {item.impact_strength:.2f} | {link_text}"
        )
    return "\n".join(lines)


def is_market_scan_prompt(prompt: str) -> bool:
    text = prompt.lower()
    patterns = (
        "most positive news",
        "top positive news",
        "best news today",
        "which companies",
        "what companies",
        "which stocks",
        "what stocks",
    )
    return any(pattern in text for pattern in patterns)


def detect_known_ticker(prompt: str) -> str | None:
    text = prompt.upper()
    company_names = {ticker: name.upper() for ticker, name in COMPANY_MAP.items()}

    # Exact ticker mentions first.
    for ticker in COMPANY_MAP:
        if f"${ticker}" in text or f" {ticker} " in f" {text} ":
            return ticker

    # Company name mentions next.
    for ticker, company_name in company_names.items():
        if company_name in text:
            return ticker

    # If the whole prompt is basically a company/ticker query, try the dynamic resolver.
    cleaned_prompt = (
        text.replace("PREDICT", "")
        .replace("ANALYZE", "")
        .replace("STOCK", "")
        .replace("SHARE", "")
        .replace("WHY", "")
        .replace("FALL", "")
        .replace("RISE", "")
        .replace("MOVE", "")
        .replace("PRICE", "")
        .replace("TODAY", "")
        .replace("TOMORROW", "")
        .strip(" ?")
    )
    if cleaned_prompt and len(cleaned_prompt.split()) <= 5:
        resolved = resolve_security(cleaned_prompt)
        if resolved.ticker != "UNKNOWN":
            return resolved.ticker

    return None


def extract_ticker(prompt):
    """Extract stock ticker from natural language prompt."""
    import re
    
    known_ticker = detect_known_ticker(prompt)
    if known_ticker:
        return known_ticker

    # Convert to uppercase for processing
    text = prompt.upper()
    
    # Support plain tickers plus suffixes such as TCS.NS / RELIANCE.BSE.
    ticker_pattern = r'\b[A-Z][A-Z0-9]{0,10}(?:\.[A-Z]{1,4})?\b'
    potential_tickers = re.findall(ticker_pattern, text)
    
    # Filter out common words that might match the pattern
    common_words = {'STOCK', 'TOMORROW', 'TODAY', 'ANALYZE', 'PREDICT', 'WHAT', 'ABOUT', 'FOR', 'THE', 'AND', 'OR', 'BUT', 'CHECK', 'PLEASE', 'HOW', 'IS', 'DOING', 'TELL', 'ME', 'THAT', 'WITH', 'ARE', 'YOU', 'CAN', 'SHOULD', 'WOULD', 'COULD', 'THIS', 'THERE', 'HERE', 'WILL', 'FROM', 'HAVE', 'BEEN', 'WHEN'}
    valid_tickers = [t for t in potential_tickers if t not in common_words and len(t) >= 2]
    
    # Score tickers based on various heuristics
    scored_tickers = []
    for ticker in valid_tickers:
        score = 0
        # Prefer longer tickers
        score += len(ticker) * 2
        # Prefer tickers that look like real stock symbols (contain vowels, not all consonants)
        if any(vowel in ticker for vowel in 'AEIOU'):
            score += 3
        # Prefer tickers not at the beginning of sentences (less likely to be verbs)
        if not text.startswith(ticker):
            score += 1
            
        scored_tickers.append((ticker, score))
    
    # Return the highest scoring ticker
    if scored_tickers:
        scored_tickers.sort(key=lambda x: x[1], reverse=True)
        return scored_tickers[0][0]
    
    # If nothing reliable was found, signal that clearly instead of guessing.
    return None


def build_market_scan_content(prompt: str, tickers: list[str]) -> str:
    orchestrator = StockAnalysisOrchestrator()
    ranked = []

    for ticker in tickers:
        result = orchestrator.run(ticker)
        evidence = result.evidence
        if not evidence:
            continue

        positive_items = [item for item in evidence if item.sentiment == "positive"]
        negative_items = [item for item in evidence if item.sentiment == "negative"]
        neutral_items = [item for item in evidence if item.sentiment == "neutral"]
        net_sentiment = (len(positive_items) - len(negative_items)) / max(len(evidence), 1)
        positive_strength = sum(item.impact_strength for item in positive_items)

        ranked.append(
            {
                "ticker": ticker,
                "company": result.prediction.company,
                "result": result,
                "positive_count": len(positive_items),
                "negative_count": len(negative_items),
                "neutral_count": len(neutral_items),
                "net_sentiment": net_sentiment,
                "positive_strength": positive_strength,
            }
        )

    ranked.sort(
        key=lambda item: (
            item["positive_count"],
            item["net_sentiment"],
            item["positive_strength"],
            item["result"].prediction.up_probability,
        ),
        reverse=True,
    )

    if not ranked:
        return "I could not find enough evidence to rank companies right now."

    top_ranked = ranked[:5]
    lines = [
        "**Market Sentiment Scan**",
        "",
        f"Question: {prompt}",
        "",
        f"Active market: {get_active_market()}",
        "",
        f"Scanned universe: {', '.join(tickers)}",
        "",
        "Ranked by positive-news count first, then sentiment balance, evidence strength, and model up-probability.",
        "",
        "**Top companies with the most positive news:**",
    ]

    for index, item in enumerate(top_ranked, start=1):
        prediction = item["result"].prediction
        positive_sources = [entry for entry in item["result"].evidence if entry.sentiment == "positive"][:2]
        source_text = (
            "; ".join(
                f"{entry.title} ({'link' if is_live_source_url(entry.url) else 'demo/no live link'})"
                for entry in positive_sources
            )
            if positive_sources
            else "No clearly positive article in current evidence."
        )
        lines.extend(
            [
                f"{index}. **{item['company']} ({item['ticker']})**",
                f"   Positive: {item['positive_count']} | Negative: {item['negative_count']} | Neutral: {item['neutral_count']}",
                f"   Outlook: {prediction.outlook} | Up probability: {prediction.up_probability:.0%} | Confidence: {prediction.confidence:.0%}",
                f"   Why it ranks here: {source_text}",
            ]
        )

    lines.extend(
        [
            "",
            "**How to verify the model is working:**",
            "- Ask for a specific ticker like `AAPL` or `TCS` and check whether the evidence links and sentiment match the prediction.",
            "- Compare the chat result with the Dashboard page for the same ticker set.",
            "- If the evidence looks off-topic, the issue is usually data collection or prompt parsing rather than the prediction formula.",
        ]
    )

    if settings.use_mock_data:
        lines.extend(
            [
                "",
                "> Warning: this scan is still using mock/demo evidence.",
            ]
        )

    return "\n".join(lines)


st.title("Chat Assistant")
st.caption("Ask for a ticker and get a next-day directional view")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Example: Analyze NVDA for tomorrow")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Running news and prediction agents..."):
            if is_market_scan_prompt(prompt):
                market = get_active_market()
                if market == "India":
                    fallback_universe = ["TCS", "INFY", "RELIANCE", "SBIN.NS", "LT.NS", "ITC.NS"]
                else:
                    fallback_universe = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
                scan_tickers = st.session_state.get("watchlist", [])
                filtered_watchlist = [
                    ticker for ticker in scan_tickers
                    if (market == "India" and (".NS" in ticker or ".BO" in ticker or ticker in {"TCS", "INFY", "RELIANCE"}))
                    or (market == "US" and ".NS" not in ticker and ".BO" not in ticker)
                ]
                content = build_market_scan_content(prompt, filtered_watchlist + [t for t in fallback_universe if t not in filtered_watchlist][:8])
            else:
                ticker = extract_ticker(prompt)
                if not ticker:
                    content = (
                        "I could not identify a supported company or ticker from that message.\n\n"
                        "Try a ticker like `AAPL`, `TSLA`, `NVDA`, `TCS`, or ask a broader question like "
                        "`What companies have the most positive news today?`"
                    )
                else:
                    result = StockAnalysisOrchestrator().run(ticker)
                    detailed_analysis = generate_detailed_analysis(result.prediction, result.evidence)
                    source_section = build_source_section(result.evidence)
                    mode_note = (
                        "> Warning: app is running in mock/demo data mode. Source links and conclusions are placeholders, not reliable live market evidence.\n\n"
                        if settings.use_mock_data
                        else ""
                    )
                    content = (
                        f"**{result.prediction.company} ({result.prediction.ticker})**\n\n"
                        f"Outlook: **{result.prediction.outlook}**  \n"
                        f"Up probability: **{result.prediction.up_probability:.0%}**  \n"
                        f"Confidence: **{result.prediction.confidence:.0%}**  \n"
                        f"Expected move: **{result.prediction.expected_move_pct}%**\n\n"
                        f"{mode_note}"
                        f"{result.answer}\n\n"
                        f"{detailed_analysis}\n\n"
                        "**Top evidence:**\n" + "\n".join(
                            f"- {e.title} ({e.sentiment}, impact {e.impact_strength:.2f})" for e in result.evidence[:5]
                        ) + "\n\n"
                        "**Source links:**\n"
                        f"{source_section}\n\n"
                        "**Analysis basis:**\n"
                        f"- Model reasoning: {result.prediction.reasoning}\n"
                        f"- Drivers: {'; '.join(result.prediction.drivers)}\n"
                        f"- Risks: {'; '.join(result.prediction.risks)}"
                    )
            st.markdown(content)
    st.session_state.messages.append({"role": "assistant", "content": content})
