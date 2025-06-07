from typing import Dict, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import os
import yfinance as yf

load_dotenv()

api = REST( # Initialize Alpaca API
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    base_url="https://paper-api.alpaca.markets"
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

def fetch_bot_equity() -> float:
    account = api.get_account()
    return float(account.equity)

def fetch_index_returns() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Fetch the last 30 days of daily returns for S&P 500 and NASDAQ indices.
    Returns:
        Tuple containing two dictionaries:
        - S&P 500 returns
        - NASDAQ returns
    """
    sp500 = yf.download('^GSPC', period='30d', interval='1d')['Close']
    nasdaq = yf.download('^IXIC', period='30d', interval='1d')['Close']

    sp500_returns = sp500.pct_change().fillna(0).cumsum() * 100
    nasdaq_returns = nasdaq.pct_change().fillna(0).cumsum() * 100

    # Format index to strings
    sp500_returns.index = sp500_returns.index.strftime('%Y-%m-%d')
    nasdaq_returns.index = nasdaq_returns.index.strftime('%Y-%m-%d')

    return move_nested_to_parent(sp500_returns.to_dict(), '^GSPC'), move_nested_to_parent(nasdaq_returns.to_dict(), '^IXIC')


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
    bot_equity = fetch_bot_equity()
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
