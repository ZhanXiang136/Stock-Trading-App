import os
import datetime as dt
from reddit_sentiment_pipeline.scrape import fetch_recent_posts
from reddit_sentiment_pipeline.sentiment_utils import Sentiment_Analyzer
from reddit_sentiment_pipeline.fine_tune import fine_tune_from_csv
from trading_engine.alpaca_trade import submit_order, get_position

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from performance_api.performance import get_performance

app = FastAPI()

# Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://stocktradingai.netlify.app"],
    allow_methods=[""],
    allow_headers=["*"]
)

@app.get("/api/performance")
def performance():
    return get_performance()

@app.get("/", include_in_schema=False)
def performance():
    return RedirectResponse(url="/docs")


MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "src/model")

def ensure_model_trained():
    if not os.path.exists(MODEL_DIR):
        print("Model not found. Fine-tuning model using training data...")
        fine_tune_from_csv(TRAIN_CSV)
    else:
        print(f"Using existing model at: {MODEL_DIR}")

if __name__ == "__main__":
    ensure_model_trained()

    print("Fetching Reddit posts...")
    hours = 72 if dt.datetime.now().weekday() == 0 else 24
    raw_posts = fetch_recent_posts(hours=hours)

    for post in raw_posts:
        title = post.get("title", "")
        body = post.get("body", "")
        comments = post.get("comments", [])
        comment_text = " ".join(comments[:3]) 
        full_text = f"{title} {body} {comment_text}".strip()
        post['text'] = full_text

    sentiment_analyzer = Sentiment_Analyzer(model_path=MODEL_DIR)

    print(f"Fetched {len(raw_posts)} posts. Analyzing sentiment...")
    analyzed = sentiment_analyzer.analyze_bulk(raw_posts)

    print("Aggregating sentiments by ticker...")
    ticker_data = sentiment_analyzer.aggregate_sentiments(analyzed)

    print("Generating trading signals...")
    signals = sentiment_analyzer.generate_signals(ticker_data)

    print("--- Trade Signals ---")
    for ticker, signal in signals.items():
        print(f"{ticker}: {signal}")

    # print("Executing trades...")
    # for ticker, signal in signals.items():
    #     if signal == "BUY":
    #         submit_order(ticker, qty=1, side="buy")
    #     elif signal == "SELL":
    #         submit_order(ticker, qty=1, side="sell")