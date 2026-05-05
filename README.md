# 📈 AI-Powered Stock Trading App

This project uses **Natural Language Processing (NLP)** and market data to generate automated trading signals based on sentiment from Reddit stock discussions. It combines a FastAPI backend, a Hugging Face sentiment model, ticker extraction, Alpaca paper trading, and performance data for a frontend dashboard.

---

## 🚀 Features

- 🤖 **Sentiment Analysis**  
  Fine-tuned Hugging Face transformer model evaluates sentiment of Reddit posts mentioning stocks.

- 💬 **Smart Ticker Extraction**  
  Recognizes ticker symbols using `$` notation, fuzzy matching (e.g., “Tesla” → `$TSLA`), named entity recognition, and alias mapping.

- 📊 **Performance Visualization**  
  Frontend dashboard built with React.js to display:
  - Bot’s equity curve over time
  - Comparison with S&P 500 and NASDAQ
  - Last updated timestamp

- 🔁 **Automated Pipeline**  
  - Scrapes recent posts from WallStreetBets
  - Parses sentiment and tickers
  - Makes buy/sell/hold decisions based on aggregated sentiment
  - Lowers the trading threshold for higher-beta stocks
  - Uses dry-run mode by default so signals can be reviewed before orders are placed

---

## 🧠 Tech Stack

- **Frontend**: React.js + Chart.js
- **Backend**: FastAPI + Python
- **ML Framework**: Hugging Face Transformers (`ProsusAI/finbert`)
- **Data Source**: Reddit API via PRAW
- **Broker API**: Alpaca API for real-time trading and equity tracking
- **Market Data**: Yahoo Finance via `yfinance` for index returns and stock beta
- **Hosting**: Render / Netlify 

---

## 📂 Directory Structure

```
/src
│
├── main.py                         # FastAPI app and pipeline orchestration
├── reddit_sentiment_pipeline/
│   ├── scrape.py                   # Reddit scraping and volatility/beta lookup
│   ├── sentiment_utils.py          # Sentiment aggregation and signal generation
│   ├── ticket_extractor.py         # Ticker name detection
│   └── fine_tune.py                # Model train/download/upload helpers
├── trading_engine/
│   └── alpaca_trade.py             # Alpaca order and position helpers
├── performance_api/
│   └── performance.py              # Portfolio/index performance endpoint
└── data/                           # Ticker maps, aliases, and datasets
```

---

## ✅ Setup Instructions

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/yourusername/stock-trading-app.git
   cd stock-trading-app
   ```

2. **Create a virtual environment and install dependencies**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. **Set up environment variables**  
   Create a `.env` file in the root with your keys:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_secret
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ALPACA_DATA_FEED=iex
   RUN_API_TOKEN=your_private_run_endpoint_token
   DRY_RUN=true
   SCHEDULED_TRADING_ENABLED=false
   SCHEDULED_TRADING_INTERVAL_SECONDS=300
   SCHEDULED_TRADING_DRY_RUN=true
   SCHEDULED_TRADING_QTY=1
   REDDIT_LOOKBACK_HOURS=24
   REDDIT_POST_LIMIT=1000
   SIGNAL_THRESHOLD=0.6
   SIGNAL_MENTION_THRESHOLD=3
   SIGNAL_CONFLICT_MARGIN=0.2
   SENTIMENT_MODEL_PATH=src/model
   SENTIMENT_USE_MODEL=true
   SENTIMENT_TRAINING_CSV=src/data/Reddit_Data.csv
   SENTIMENT_BASE_MODEL=ProsusAI/finbert
   ENFORCE_MARKET_HOURS=true
   MAX_DAILY_TRADES=10
   MAX_POSITION_VALUE=1000
   ```

   The code also supports Alpaca's standard `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` variable names. `DRY_RUN` defaults to `true`; set it to `false` only when you intentionally want live paper-trading orders submitted.
   If the Hugging Face model weights are not available locally, the app fine-tunes `SENTIMENT_BASE_MODEL` with `SENTIMENT_TRAINING_CSV` and saves the result to `SENTIMENT_MODEL_PATH`. Set `SENTIMENT_USE_MODEL=false` to use the lightweight local sentiment fallback instead.

4. **Run the Backend API**  
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Start the Frontend**  
   Open https://zhanxiangzheng.me/stocktradingai to view the bot's performance history compared to market indexes.
   At this time, the frontend expects the backend API at `http://127.0.0.1:8000/`, so run the backend locally.

---

## 🔌 API Endpoints

- `GET /api/performance`  
  Returns bot equity history plus S&P 500 and NASDAQ return data.

- `GET /api/init`  
  Trains/loads the sentiment model if needed.

- `POST /api/run?dry_run=true&qty=10`  
  Runs the Reddit sentiment pipeline. This endpoint requires either:
  ```bash
  Authorization: Bearer your_private_run_endpoint_token
  ```
  or:
  ```bash
  x-api-key: your_private_run_endpoint_token
  ```

  By default, `dry_run=true`, so the endpoint returns signals without placing orders. Use `dry_run=false` only for Alpaca paper-trading execution.

  You can temporarily make a run more active without editing `.env`:
  ```bash
  curl -X POST "http://127.0.0.1:8000/api/run?dry_run=true&qty=1&threshold=0.52&mention_threshold=1&conflict_margin=0.0" \
    -H "Authorization: Bearer your_private_run_endpoint_token"
  ```

  For repeated paper-trading runs, set the same knobs in `.env`. A more active profile might use:
  ```
  SIGNAL_THRESHOLD=0.52
  SIGNAL_MENTION_THRESHOLD=1
  SIGNAL_CONFLICT_MARGIN=0.0
  MAX_DAILY_TRADES=50
  MAX_POSITION_VALUE=250
  ```
  Keep `DRY_RUN=true` until you have reviewed the trade log and signal quality.

- `GET /api/scheduler`  
  Returns scheduler status, including whether it is enabled, whether a run is currently active, the last result, and the next scheduled run time.

  To run the pipeline every 5 minutes, set this in `.env` and restart the backend:
  ```
  SCHEDULED_TRADING_ENABLED=true
  SCHEDULED_TRADING_INTERVAL_SECONDS=300
  SCHEDULED_TRADING_RUN_ON_STARTUP=true
  SCHEDULED_TRADING_DRY_RUN=true
  SCHEDULED_TRADING_QTY=1
  ```

  To submit Alpaca paper orders on the schedule, change only this after reviewing dry-run results:
  ```
  SCHEDULED_TRADING_DRY_RUN=false
  ```

---

## 📈 Signal Logic

Signals are generated from ticker-level aggregated sentiment:

- Requires at least 3 mentions by default.
- Weights positive and negative evidence by model confidence score.
- Holds when positive and negative evidence is too conflicted.
- Signal aggressiveness can be tuned with `SIGNAL_THRESHOLD`, `SIGNAL_MENTION_THRESHOLD`, and `SIGNAL_CONFLICT_MARGIN`.
- Fetches each ticker's beta with `yfinance`.
- For beta above `1.0`, lowers the trading threshold by `0.05` per beta point.
- The threshold is capped at a minimum of `0.45` to avoid trading on weak sentiment.

Example: with a base threshold of `0.60`, a stock with beta `2.0` uses an adjusted threshold of about `0.55`.

---

## 🛡️ Trade Safety

When `dry_run=false`, the app runs risk checks before submitting an Alpaca paper order:

- Blocks orders when the Alpaca market clock is closed if `ENFORCE_MARKET_HOURS=true`.
- Blocks new buys when already holding that ticker.
- Blocks sells when there is no current position.
- Blocks buys whose estimated order value exceeds `MAX_POSITION_VALUE`.
- Blocks orders after `MAX_DAILY_TRADES` submitted trades for the current UTC day.

Every signal is logged to `src/data/trade_decisions.csv`, including dry-run signals, submitted orders, risk-check reasons, mentions, sentiment scores, and beta. This file is ignored by git.

---

## 🧪 Training Data

Fine-tuning expects a CSV with:

- `text`: the post/comment text.
- `label`: one of `-1`, `0`, `1`, `negative`, `neutral`, `positive`, `bearish`, or `bullish`.

The loader drops empty and duplicate text rows, validates labels, requires at least two classes, and uses a reproducible stratified split. For better trading signals, use finance-specific/social-market sentiment data rather than generic sentiment datasets.

---

## 🚀 Deployment

This repo includes Render-style deployment files:

- `runtime.txt`: `python-3.12.7`
- `Procfile`: `web: uvicorn src.main:app --host 0.0.0.0 --port $PORT`

Set the same environment variables from setup in your hosting provider. Keep `RUN_API_TOKEN` private.

---

## 👤 Acknowledgments

This app was trained using data from Kaggle, provided under the Creative Commons license by:

- Charan Gowda  
- Anirudh  
- Akshay Pai  
- Chaithanya Kumar A

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
