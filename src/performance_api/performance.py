from typing import Tuple, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
from contextlib import redirect_stderr, redirect_stdout
import io
import os
import time
from urllib.parse import urlencode
import yfinance as yf
import pandas as pd

load_dotenv()

_performance_cache: dict[str, Any] = {
    "timestamp": 0.0,
    "data": None,
}

def get_alpaca_credentials() -> tuple[str, str]:
    api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")
    api_key = api_key.strip() if api_key else None
    secret_key = secret_key.strip() if secret_key else None

    if not api_key or not secret_key:
        raise RuntimeError(
            "Missing Alpaca credentials. Set APCA_API_KEY_ID/APCA_API_SECRET_KEY "
            "or ALPACA_API_KEY/ALPACA_SECRET_KEY."
        )
    return api_key, secret_key

def get_alpaca_api() -> REST:
    api_key, secret_key = get_alpaca_credentials()
    return REST(
        api_key,
        secret_key,
        base_url=get_alpaca_base_url()
    )

def get_alpaca_base_url() -> str:
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").strip().rstrip("/")
    if base_url.endswith("/v2"):
        base_url = base_url[:-3]
    return base_url

def fetch_bot_equity_over_time(days: int = 30) -> dict:
    history = get_alpaca_api().get_portfolio_history(
        period=f"{days}D",
        timeframe="1D"
    )

    equity_timeline = dict(zip(history.timestamp, history.equity))

    # Get the starting equity to compute percentage change
    timestamps = sorted(equity_timeline.keys())
    if not timestamps:
        return {}

    starting_equity = equity_timeline[timestamps[0]] if equity_timeline[timestamps[0]] else 100000

    # Calculate percentage change
    formatted = {
        datetime.fromtimestamp(ts).strftime("%Y-%m-%d"): ((equity - starting_equity) / starting_equity) * 100

        for ts, equity in equity_timeline.items()
    }

    return formatted

def extract_close_prices(prices: pd.DataFrame, symbol: str) -> pd.Series:
    if prices is None or prices.empty:
        raise RuntimeError(f"No price data returned for {symbol}")

    close = None
    if isinstance(prices.columns, pd.MultiIndex):
        if "Close" in prices.columns.get_level_values(0):
            close = prices["Close"]
        elif "Close" in prices.columns.get_level_values(1):
            close = prices.xs("Close", axis=1, level=1)
    elif "Close" in prices:
        close = prices["Close"]

    if close is None:
        raise RuntimeError(f"No close price data returned for {symbol}")

    if isinstance(close, pd.DataFrame):
        if symbol in close:
            close = close[symbol]
        elif len(close.columns) == 1:
            close = close.iloc[:, 0]
        else:
            raise RuntimeError(f"No close price data returned for {symbol}")

    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        raise RuntimeError(f"No close price data returned for {symbol}")

    return close

def fetch_single_index_returns(symbol: str) -> Dict[str, Any]:
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        prices = yf.download(
            symbol,
            period='30d',
            interval='1d',
            progress=False,
            threads=False,
        )

    close = extract_close_prices(prices, symbol)
    starting_close = close.iloc[0]
    if not starting_close:
        raise RuntimeError(f"Invalid starting close price returned for {symbol}")

    returns = ((close / starting_close) - 1) * 100
    returns.index = pd.to_datetime(returns.index).strftime('%Y-%m-%d')
    return {date: float(value) for date, value in returns.to_dict().items()}

def fetch_fred_index_returns(series_id: str, days: int = 30) -> Dict[str, Any]:
    start_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
    query = urlencode({"id": series_id, "observation_start": start_date})
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"

    prices = pd.read_csv(url)
    date_column = "observation_date"
    if prices is None or prices.empty or date_column not in prices or series_id not in prices:
        raise RuntimeError(f"No FRED price data returned for {series_id}")

    close = pd.to_numeric(prices[series_id], errors="coerce")
    prices = prices.assign(close=close).dropna(subset=["close"]).tail(days)
    if prices.empty:
        raise RuntimeError(f"No FRED close price data returned for {series_id}")

    starting_close = prices["close"].iloc[0]
    if not starting_close:
        raise RuntimeError(f"Invalid starting close price returned for {series_id}")

    returns = ((prices["close"] / starting_close) - 1) * 100
    return {
        date: float(value)
        for date, value in zip(prices[date_column], returns)
    }

def fetch_benchmark_returns(yahoo_symbol: str, fred_series_id: str) -> Dict[str, Any]:
    try:
        return fetch_single_index_returns(yahoo_symbol)
    except Exception as yahoo_exc:
        try:
            return fetch_fred_index_returns(fred_series_id)
        except Exception as fred_exc:
            raise RuntimeError(
                f"Yahoo failed for {yahoo_symbol}: {yahoo_exc}; "
                f"FRED failed for {fred_series_id}: {fred_exc}"
            ) from fred_exc

def fetch_index_returns() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, str]]:
    """
    Fetch the last 30 days of daily returns for S&P 500 and NASDAQ indices.
    Returns:
        Tuple containing two dictionaries:
        - S&P 500 returns
        - NASDAQ returns
    """
    errors = {}

    try:
        sp500 = fetch_benchmark_returns('^GSPC', 'SP500')
    except Exception as exc:
        sp500 = {}
        errors["sp500"] = str(exc)

    try:
        nasdaq = fetch_benchmark_returns('^IXIC', 'NASDAQCOM')
    except Exception as exc:
        nasdaq = {}
        errors["nasdaq"] = str(exc)

    return sp500, nasdaq, errors

def get_performance() -> Dict[str, Any]:
    """
    Fetch the bot's equity and the last 30 days of daily returns for S&P 500 and NASDAQ indices.
    Returns:
        Dictionary containing:
        - Timestamp of the request
        - Bot equity
        - S&P 500 returns
        - NASDAQ returns
    """
    cache_ttl = int(os.getenv("PERFORMANCE_CACHE_SECONDS", "60"))
    now = time.time()
    cached_data = _performance_cache.get("data")
    if cached_data and now - _performance_cache["timestamp"] < cache_ttl:
        return cached_data

    bot_equity_error = None
    try:
        bot_equity = fetch_bot_equity_over_time()
    except Exception as exc:
        bot_equity = {}
        bot_equity_error = str(exc)

    sp500, nasdaq, index_errors = fetch_index_returns()

    response = {
        "timestamp": datetime.utcnow().isoformat(),
        "bot_equity": bot_equity,
        "sp500": sp500,
        "nasdaq": nasdaq
    }
    if bot_equity_error:
        response["bot_equity_error"] = bot_equity_error
    if index_errors:
        response["index_errors"] = index_errors
    _performance_cache["timestamp"] = now
    _performance_cache["data"] = response
    return response

if __name__ == "__main__":
    # For testing purposes
    print(get_performance())
