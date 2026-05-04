import csv
import datetime as dt
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TRADE_LOG_PATH = DATA_DIR / "trade_decisions.csv"

FIELDNAMES = [
    "timestamp",
    "ticker",
    "signal",
    "qty",
    "dry_run",
    "submitted",
    "reason",
    "mentions",
    "positive",
    "negative",
    "neutral",
    "positive_score",
    "negative_score",
    "neutral_score",
    "volatility",
]

def append_trade_decision(
    ticker: str,
    signal: str,
    qty: int,
    dry_run: bool,
    submitted: bool,
    reason: str,
    ticker_data: dict[str, Any] | None = None,
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ticker_data = ticker_data or {}
    row = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "ticker": ticker,
        "signal": signal,
        "qty": qty,
        "dry_run": dry_run,
        "submitted": submitted,
        "reason": reason,
        "mentions": ticker_data.get("mentions", ""),
        "positive": ticker_data.get("positive", ""),
        "negative": ticker_data.get("negative", ""),
        "neutral": ticker_data.get("neutral", ""),
        "positive_score": ticker_data.get("positive_score", ""),
        "negative_score": ticker_data.get("negative_score", ""),
        "neutral_score": ticker_data.get("neutral_score", ""),
        "volatility": ticker_data.get("volatility", ""),
    }

    needs_header = not TRADE_LOG_PATH.exists() or TRADE_LOG_PATH.stat().st_size == 0
    with open(TRADE_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)

def count_submitted_trades_today() -> int:
    if not TRADE_LOG_PATH.exists():
        return 0

    today = dt.datetime.now(dt.UTC).date()
    count = 0
    with open(TRADE_LOG_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                timestamp = dt.datetime.fromisoformat(row.get("timestamp", ""))
            except ValueError:
                continue
            if timestamp.date() == today and row.get("submitted") == "True":
                count += 1
    return count
