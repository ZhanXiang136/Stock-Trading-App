from typing import Tuple, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import os
import yfinance as yf
import pandas as pd

load_dotenv()

def get_alpaca_credentials() -> tuple[str, str]:
    api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

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
        base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    )

def move_nested_to_parent(data: Dict[str, Any], key: str) -> Dict:
    """
    Move nested dictionary contents to the parent level.
    If the key exists and is a dictionary, its contents are merged into the parent dictionary.
    """
    # If the key exists and is a dictionary, merge its contents into the parent dictionary
    if key in data and isinstance(data[key], dict):
        nested = data.pop(key)  # Remove the nested dict
        data.update(nested)     # Add its contents to the parent
    return data

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

def fetch_index_returns() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Fetch the last 30 days of daily returns for S&P 500 and NASDAQ indices.
    Returns:
        Tuple containing two dictionaries:
        - S&P 500 returns
        - NASDAQ returns
    """
    import pandas as pd
    
    sp500 = yf.download('^GSPC', period='30d', interval='1d', progress=False)['Close']
    nasdaq = yf.download('^IXIC', period='30d', interval='1d', progress=False)['Close']

    sp500_returns = sp500.pct_change().fillna(0).cumsum() * 100
    nasdaq_returns = nasdaq.pct_change().fillna(0).cumsum() * 100

    # Convert index safely before formatting
    sp500_returns.index = pd.to_datetime(sp500_returns.index).strftime('%Y-%m-%d')
    nasdaq_returns.index = pd.to_datetime(nasdaq_returns.index).strftime('%Y-%m-%d')

    return (
        move_nested_to_parent(sp500_returns.to_dict(), '^GSPC'),
        move_nested_to_parent(nasdaq_returns.to_dict(), '^IXIC')
    )

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
    bot_equity = fetch_bot_equity_over_time()
    sp500, nasdaq = fetch_index_returns()
    print("DEBUG:", {
    "sp500": list(sp500.keys())[:5],
    "nasdaq": list(nasdaq.keys())[:5]
})
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "bot_equity": bot_equity,
        "sp500": sp500,
        "nasdaq": nasdaq
    }

if __name__ == "__main__":
    # For testing purposes
    print(get_performance())
