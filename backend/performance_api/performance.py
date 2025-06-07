import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from yfinance import download
from datetime import datetime
import pandas as pd

load_dotenv()

api = tradeapi.REST(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    base_url="https://paper-api.alpaca.markets"
)

def fetch_bot_equity():
    account = api.get_account()
    return float(account.equity)

def fetch_index_returns():
    sp500 = download('^GSPC', period='30d', interval='1d')['Close']
    nasdaq = download('^IXIC', period='30d', interval='1d')['Close']
    sp500_pct = sp500.pct_change().fillna(0).cumsum() * 100
    nasdaq_pct = nasdaq.pct_change().fillna(0).cumsum() * 100
    return sp500_pct.to_dict(), nasdaq_pct.to_dict()

def get_performance():
    bot_equity = fetch_bot_equity()
    sp500, nasdaq = fetch_index_returns()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "bot_equity": bot_equity,
        "sp500": sp500,
        "nasdaq": nasdaq
    }
