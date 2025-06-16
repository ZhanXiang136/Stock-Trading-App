import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load API credentials from .env
load_dotenv()

# Initialize Alpaca API
api = tradeapi.REST(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    base_url="https://paper-api.alpaca.markets"
)

def submit_order(symbol: str, qty: int, side: str):
    """
    Submit a market order to Alpaca.
    side: 'buy' or 'sell'
    """
    if side not in ["buy", "sell"]:
        raise ValueError("Side must be 'buy' or 'sell'")
    
    try:
        order = api.submit_order(
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
        pos = api.get_position(symbol)
        print(f"You own {pos.qty} share(s) of {symbol} at ${pos.avg_entry_price}")
        return pos
    except:
        print(f"No position found for {symbol}")
        return None

if __name__ == "__main__":
    print(submit_order("AAPL", 1, "buy"))   # Buy 1 share
    print(get_position("AAPL"))
    print(submit_order("AAPL", 1, "sell"))  # Sell 1 share