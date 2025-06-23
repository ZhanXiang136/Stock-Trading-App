import os
import datetime as dt
from src.reddit_sentiment_pipeline.scrape import fetch_recent_posts
from src.reddit_sentiment_pipeline.sentiment_utils import Sentiment_Analyzer
from src.reddit_sentiment_pipeline.fine_tune import download_model_from_huggingface
from src.trading_engine.alpaca_trade import submit_order, get_position
from src.performance_api.performance import get_performance

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException



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

@app.get("/api/run")
def run_app():
    return main()

@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return RedirectResponse(url="/docs")
    return await app.default_exception_handler(request, exc)

@app.get("/", include_in_schema=False)
def performance():
    return RedirectResponse(url="/docs")
    

MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "src//model")

def ensure_mode_exist():
    if not os.path.exists(MODEL_DIR):
        print("Model not found. Fine-tuning model using training data...")
        download_model_from_huggingface()
    else:
        print(f"Using existing model at: {MODEL_DIR}")

def main():
    try:
        ensure_mode_exist()

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

        print("Executing trades...")
        for ticker, signal in signals.items():
            if signal == "BUY":
                submit_order(ticker, qty=1, side="buy")
            elif signal == "SELL":
                submit_order(ticker, qty=1, side="sell")
        return {"status": "success", "signals": signals}
    except Exception as e:
        return {"Exception Type": type(e).__name__, "Exception Message": str(e)}

if __name__ == "__main__":
    main()