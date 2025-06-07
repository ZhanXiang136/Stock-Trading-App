from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import os
import yfinance as yf

load_dotenv()

api = REST(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    base_url="https://paper-api.alpaca.markets"
)

def move_nested_to_parent(data, key):
    if key in data and isinstance(data[key], dict):
        nested = data.pop(key)  # Remove the nested dict
        data.update(nested)     # Add its contents to the parent
    return data

def fetch_bot_equity():
    account = api.get_account()
    return float(account.equity)

def fetch_index_returns():
    import yfinance as yf

    sp500 = yf.download('^GSPC', period='30d', interval='1d')['Close']
    nasdaq = yf.download('^IXIC', period='30d', interval='1d')['Close']

    sp500_returns = sp500.pct_change().fillna(0).cumsum() * 100
    nasdaq_returns = nasdaq.pct_change().fillna(0).cumsum() * 100

    # Format index to strings
    sp500_returns.index = sp500_returns.index.strftime('%Y-%m-%d')
    nasdaq_returns.index = nasdaq_returns.index.strftime('%Y-%m-%d')

    return move_nested_to_parent(sp500_returns.to_dict(), '^GSPC'), move_nested_to_parent(nasdaq_returns.to_dict(), '^IXIC')


def get_performance():
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
