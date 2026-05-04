import os
import secrets
import datetime as dt
from src.reddit_sentiment_pipeline.sentiment_utils import Sentiment_Analyzer

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

app = FastAPI()
sentiment_analyzer = None

# Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://stocktradingai.netlify.app"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

@app.get("/api/performance")
def performance():
    from src.performance_api.performance import get_performance

    return get_performance()

@app.post("/api/run")
def run_app(
    request: Request,
    dry_run: bool = Query(True, description="When true, generate signals without placing orders."),
    qty: int = Query(10, ge=1, le=100),
):
    require_run_token(request)
    return main(dry_run=dry_run, qty=qty)

@app.get("/api/init")
def init_app():
    global sentiment_analyzer
    if sentiment_analyzer is None:
        sentiment_analyzer = get_sentiment_analyzer()
        return {"status": "Sentiment Analyzer initialized"}
    return {"status": "Sentiment Analyzer already initialized"}

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.get("/", include_in_schema=False)
def performance():
    return RedirectResponse(url="/docs")
    

MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "src/model")

def ensure_model_exists():
    if not os.path.exists(MODEL_DIR):
        from src.reddit_sentiment_pipeline.fine_tune import download_model_from_huggingface

        print("Model not found. Downloading from Repo...")
        download_model_from_huggingface()
    else:
        print(f"Using existing model at: {MODEL_DIR}")

def get_sentiment_analyzer():
    global sentiment_analyzer

    ensure_model_exists()
    if sentiment_analyzer is None:
        sentiment_analyzer = Sentiment_Analyzer()
    return sentiment_analyzer

def require_run_token(request: Request):
    expected_token = os.getenv("RUN_API_TOKEN") or os.getenv("API_RUN_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="RUN_API_TOKEN is not configured.")

    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip()
    api_key = request.headers.get("x-api-key", "").strip()

    valid_bearer = bool(bearer_token) and secrets.compare_digest(expected_token, bearer_token)
    valid_api_key = bool(api_key) and secrets.compare_digest(expected_token, api_key)

    if not valid_bearer and not valid_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing run token.")

def main(dry_run: bool | None = None, qty: int = 10):
    try:
        analyzer = get_sentiment_analyzer()
        if dry_run is None:
            dry_run = os.getenv("DRY_RUN", "true").lower() != "false"

        print("Fetching Reddit posts...")
        from src.reddit_sentiment_pipeline.scrape import fetch_recent_posts

        hours = 72 if dt.datetime.now().weekday() == 0 else 24
        raw_posts = fetch_recent_posts(hours=hours)

        for post in raw_posts:
            title = post.get("title", "")
            body = post.get("body", "")
            comments = post.get("comments", [])
            comment_text = " ".join(comments[:3]) 
            full_text = f"{title} {body} {comment_text}".strip()
            post['text'] = full_text

        print(f"Fetched {len(raw_posts)} posts. Analyzing sentiment...")
        analyzed = analyzer.analyze_bulk(raw_posts)
        print(analyzed)

        print("Aggregating sentiments by ticker...")
        ticker_data = analyzer.aggregate_sentiments(analyzed)
        print(ticker_data)

        print("Fetching volatility data...")
        from src.reddit_sentiment_pipeline.scrape import get_volatility

        volatility_data = get_volatility(list(ticker_data.keys())) if ticker_data else {}
        for ticker, volatility in volatility_data.items():
            if ticker in ticker_data:
                ticker_data[ticker]['volatility'] = volatility
        print(volatility_data)

        print("Generating trading signals...")
        signals = analyzer.generate_signals(ticker_data)
        print(signals)

        print("--- Trade Signals ---")
        for ticker, signal in signals.items():
            print(f"{ticker}: {signal}")

        executed_orders = []
        from src.trading_engine.trade_log import append_trade_decision

        if dry_run:
            print("Dry run enabled. Skipping trade execution.")
            for ticker, signal in signals.items():
                append_trade_decision(
                    ticker=ticker,
                    signal=signal,
                    qty=qty,
                    dry_run=True,
                    submitted=False,
                    reason="dry run",
                    ticker_data=ticker_data.get(ticker),
                )
        else:
            from src.trading_engine.alpaca_trade import submit_order
            from src.trading_engine.risk import evaluate_trade_risk

            print("Executing trades...")
            for ticker, signal in signals.items():
                submitted = False
                reason = "hold signal"

                if signal == "BUY":
                    risk_decision = evaluate_trade_risk(ticker, qty=qty, side="buy")
                    reason = risk_decision.reason
                    if risk_decision.allowed:
                        order = submit_order(ticker, qty=qty, side="buy")
                        submitted = order is not None
                        executed_orders.append(order)
                elif signal == "SELL":
                    risk_decision = evaluate_trade_risk(ticker, qty=qty, side="sell")
                    reason = risk_decision.reason
                    if risk_decision.allowed:
                        order = submit_order(ticker, qty=qty, side="sell")
                        submitted = order is not None
                        executed_orders.append(order)

                append_trade_decision(
                    ticker=ticker,
                    signal=signal,
                    qty=qty,
                    dry_run=False,
                    submitted=submitted,
                    reason=reason,
                    ticker_data=ticker_data.get(ticker),
                )
        return {
            "status": "success",
            "dry_run": dry_run,
            "signals": signals,
            "orders_submitted": len([order for order in executed_orders if order is not None]),
        }
    except Exception as e:
        return {"Exception Type": type(e).__name__, "Exception Message": str(e)}

def serve():
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
