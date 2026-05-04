import asyncio
import os
import secrets
import datetime as dt
from contextlib import suppress
from pathlib import Path
from src.reddit_sentiment_pipeline.sentiment_utils import Sentiment_Analyzer

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

load_dotenv()

app = FastAPI()
sentiment_analyzer = None
scheduled_task = None
scheduled_run_lock = asyncio.Lock()
scheduled_state = {
    "enabled": False,
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_result": None,
    "last_error": None,
    "next_run_at": None,
}

# Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://stocktradingai.netlify.app",
    ],
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
    threshold: float | None = Query(None, ge=0.5, le=1.0),
    mention_threshold: int | None = Query(None, ge=1, le=25),
    conflict_margin: float | None = Query(None, ge=0.0, le=1.0),
):
    require_run_token(request)
    return main(
        dry_run=dry_run,
        qty=qty,
        threshold=threshold,
        mention_threshold=mention_threshold,
        conflict_margin=conflict_margin,
    )

@app.get("/api/init")
def init_app():
    global sentiment_analyzer
    if sentiment_analyzer is None:
        sentiment_analyzer = get_sentiment_analyzer()
        return {"status": "Sentiment Analyzer initialized"}
    return {"status": "Sentiment Analyzer already initialized"}

@app.get("/api/scheduler")
def scheduler_status():
    return scheduled_state

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
MODEL_WEIGHT_FILENAMES = {
    "pytorch_model.bin",
    "model.safetensors",
    "tf_model.h5",
    "model.ckpt.index",
    "flax_model.msgpack",
}

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}

def model_has_weights(model_dir: str) -> bool:
    path = Path(model_dir)
    if not path.exists() or not path.is_dir():
        return False
    return any((path / filename).exists() for filename in MODEL_WEIGHT_FILENAMES)

def ensure_model_exists():
    if not _env_bool("SENTIMENT_USE_MODEL", True):
        print("SENTIMENT_USE_MODEL=false. Using lightweight local sentiment fallback.")
        return

    if not model_has_weights(MODEL_DIR):
        from src.reddit_sentiment_pipeline.fine_tune import download_model_from_huggingface

        print(f"Model weights not found in {MODEL_DIR}. Downloading from Hugging Face...")
        download_model_from_huggingface()

    if not model_has_weights(MODEL_DIR):
        raise RuntimeError(
            f"Model download did not produce a checkpoint in {MODEL_DIR}. "
            "Expected one of: " + ", ".join(sorted(MODEL_WEIGHT_FILENAMES))
        )

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

def get_scheduled_run_config() -> dict:
    return {
        "dry_run": _env_bool("SCHEDULED_TRADING_DRY_RUN", True),
        "qty": _env_int("SCHEDULED_TRADING_QTY", _env_int("TRADE_QTY", 1)),
        "threshold": _env_float("SIGNAL_THRESHOLD", 0.6),
        "mention_threshold": _env_int("SIGNAL_MENTION_THRESHOLD", 3),
        "conflict_margin": _env_float("SIGNAL_CONFLICT_MARGIN", 0.2),
    }

async def run_scheduled_pipeline_once():
    if scheduled_run_lock.locked():
        print("Scheduled trading skipped because the previous run is still active.")
        return

    async with scheduled_run_lock:
        scheduled_state["running"] = True
        scheduled_state["last_started_at"] = dt.datetime.now(dt.UTC).isoformat()
        scheduled_state["last_error"] = None

        try:
            result = await asyncio.to_thread(main, **get_scheduled_run_config())
            scheduled_state["last_result"] = result
            if isinstance(result, dict) and "Exception Type" in result:
                scheduled_state["last_error"] = result
        except Exception as exc:
            scheduled_state["last_error"] = {
                "Exception Type": type(exc).__name__,
                "Exception Message": str(exc),
            }
            scheduled_state["last_result"] = None
            print(f"Scheduled trading failed: {type(exc).__name__}: {exc}")
        finally:
            scheduled_state["running"] = False
            scheduled_state["last_finished_at"] = dt.datetime.now(dt.UTC).isoformat()

async def scheduled_trading_loop():
    interval_seconds = max(60, _env_int("SCHEDULED_TRADING_INTERVAL_SECONDS", 300))
    run_on_startup = _env_bool("SCHEDULED_TRADING_RUN_ON_STARTUP", True)
    scheduled_state["enabled"] = True

    try:
        if run_on_startup:
            await run_scheduled_pipeline_once()

        while True:
            next_run = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=interval_seconds)
            scheduled_state["next_run_at"] = next_run.isoformat()
            await asyncio.sleep(interval_seconds)
            await run_scheduled_pipeline_once()
    except asyncio.CancelledError:
        scheduled_state["enabled"] = False
        scheduled_state["next_run_at"] = None
        raise

@app.on_event("startup")
async def start_scheduled_trading():
    global scheduled_task
    if not _env_bool("SCHEDULED_TRADING_ENABLED", False):
        scheduled_state["enabled"] = False
        return

    if scheduled_task is None or scheduled_task.done():
        scheduled_task = asyncio.create_task(scheduled_trading_loop())

@app.on_event("shutdown")
async def stop_scheduled_trading():
    global scheduled_task
    if scheduled_task is None:
        return

    scheduled_task.cancel()
    with suppress(asyncio.CancelledError):
        await scheduled_task
    scheduled_task = None

def main(
    dry_run: bool | None = None,
    qty: int = 10,
    threshold: float | None = None,
    mention_threshold: int | None = None,
    conflict_margin: float | None = None,
):
    try:
        analyzer = get_sentiment_analyzer()
        if dry_run is None:
            dry_run = os.getenv("DRY_RUN", "true").lower() != "false"

        print("Fetching Reddit posts...")
        from src.reddit_sentiment_pipeline.scrape import fetch_recent_posts

        default_hours = 72 if dt.datetime.now().weekday() == 0 else 24
        hours = _env_int("REDDIT_LOOKBACK_HOURS", default_hours)
        post_limit = _env_int("REDDIT_POST_LIMIT", 1000)
        raw_posts = fetch_recent_posts(hours=hours, limit=post_limit)

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
        threshold = threshold if threshold is not None else _env_float("SIGNAL_THRESHOLD", 0.6)
        mention_threshold = (
            mention_threshold
            if mention_threshold is not None
            else _env_int("SIGNAL_MENTION_THRESHOLD", 3)
        )
        conflict_margin = (
            conflict_margin
            if conflict_margin is not None
            else _env_float("SIGNAL_CONFLICT_MARGIN", 0.2)
        )
        signals = analyzer.generate_signals(
            ticker_data,
            threshold=threshold,
            mention_threshold=mention_threshold,
            conflict_margin=conflict_margin,
        )
        print(signals)

        print("--- Trade Signals ---")
        for ticker, signal in signals.items():
            print(f"{ticker}: {signal}")

        executed_orders = []
        from src.trading_engine.trade_log import append_trade_decision

        if dry_run:
            print("Dry run enabled. Skipping trade execution.")
            for ticker, signal in signals.items():
                print(f"Skipping {ticker} {signal}: dry run")
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
                    else:
                        print(f"Skipping {ticker} BUY: {reason}")
                elif signal == "SELL":
                    risk_decision = evaluate_trade_risk(ticker, qty=qty, side="sell")
                    reason = risk_decision.reason
                    if risk_decision.allowed:
                        order = submit_order(ticker, qty=qty, side="sell")
                        submitted = order is not None
                        executed_orders.append(order)
                    else:
                        print(f"Skipping {ticker} SELL: {reason}")
                else:
                    print(f"Skipping {ticker} {signal}: hold signal")

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
            "settings": {
                "qty": qty,
                "reddit_lookback_hours": hours,
                "reddit_post_limit": post_limit,
                "signal_threshold": threshold,
                "signal_mention_threshold": mention_threshold,
                "signal_conflict_margin": conflict_margin,
            },
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
