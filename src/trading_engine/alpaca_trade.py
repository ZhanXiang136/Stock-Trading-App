import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load API credentials from .env
load_dotenv()

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

def get_alpaca_api():
    api_key, secret_key = get_alpaca_credentials()
    return tradeapi.REST(
        api_key,
        secret_key,
        base_url=get_alpaca_base_url()
    )

def get_alpaca_base_url() -> str:
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").strip().rstrip("/")
    if base_url.endswith("/v2"):
        base_url = base_url[:-3]
    return base_url

def submit_order(symbol: str, qty: int, side: str):
    """
    Submit a market order to Alpaca.
    side: 'buy' or 'sell'
    """
    qty *= 10
    if side not in ["buy", "sell"]:
        raise ValueError("Side must be 'buy' or 'sell'")
    
    try:
        order = get_alpaca_api().submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type='market',
            time_in_force='gtc'
        )
        print(f"✅ {side.upper()} order placed for {qty} share(s) of {symbol}")
        return order
    except Exception as e:
        print(f"Failed to {side} {symbol}: {e}")
        return None

def get_position(symbol: str):
    """Get current position for a stock symbol."""
    try:
        pos = get_alpaca_api().get_position(symbol)
        print(f"You own {pos.qty} share(s) of {symbol} at ${pos.avg_entry_price}")
        return pos
    except:
        print(f"No position found for {symbol}")
        return None

if __name__ == "__main__":
    print(submit_order("AAPL", 1, "buy"))   # Buy 1 share
    print(get_position("AAPL"))
    print(submit_order("AAPL", 1, "sell"))  # Sell 1 share
