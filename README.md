# Stock AI Predict

A multipage Streamlit app for stock research and directional forecasting across US and Indian equities. The project combines news-driven short-term analysis with a machine-learning forecast page that can train on up to 10 years of price history and generate tomorrow and next-week directional views.

## Features
- Chat assistant for ticker-specific analysis and market-wide positive-news scans
- News, sentiment, and price-feature pipeline for short-term stock outlooks
- Dynamic company and ticker resolution for common US and Indian stocks
- ML Forecast page with historical features, tomorrow forecast, next-week forecast, and final recommendation
- Interactive charts for last week, last month, last 6 months, last year, and custom date ranges
- Live-data fallback handling with diagnostics when providers fail
- Multipage Streamlit UI for dashboard, chat, company analysis, backtest, and ML forecast

## Project Layout
```bash
stock_ai_project/
├── app.py
├── pages/
├── agents/
├── services/
├── ml/
├── db/
├── utils/
├── prompts/
├── data/
├── .env
└── requirements.txt
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5-mini
NEWSAPI_KEY=your_newsapi_key
ALPHAVANTAGE_API_KEY=your_alphavantage_key
X_BEARER_TOKEN=your_x_token
USE_MOCK_DATA=false
DEFAULT_MARKET=US
```

## Run
```bash
streamlit run app.py
```

## How It Works
1. `CompanyService` resolves tickers or company names and normalizes common US and India symbols.
2. `NewsAgent` gathers content from news, official updates, and social posts.
3. `SentimentAgent` extracts structured sentiment with OpenAI when available, otherwise falls back to rules.
4. `PredictionAgent` combines sentiment balance with price and volume features for near-term outlooks.
5. `ML Forecast` trains random-forest models on historical OHLCV data to predict tomorrow and next-week direction.

If `USE_MOCK_DATA=true`, the app runs in demo mode and responses should not be treated as reliable market analysis. When live market data is unavailable, the app surfaces diagnostics and warns before falling back to synthetic history.

## Roadmap
- Replace mock official source service with company IR and exchange feeds
- Replace mock X service with an official social-data source
- Add stronger exchange-specific symbol resolution and cached metadata
- Store articles, predictions, and model runs in PostgreSQL
- Add real labeled backtesting and richer evaluation dashboards
- Add source credibility weighting and regional market support

## Notes
- This project is for research and prototyping only.
- It is not financial advice.
- Short-term stock movement is noisy, so outputs should be treated as probabilistic signals rather than guarantees.
