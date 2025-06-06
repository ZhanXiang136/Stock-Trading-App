
import os
import alpaca_trade_api as tradeapi

api = tradeapi.REST(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    base_url="https://paper-api.alpaca.markets"
)

def submit_order(symbol, qty, side="buy"):
    api.submit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        type="market",
        time_in_force="gtc"
    )
    print(f"Order submitted: {side.upper()} {qty} shares of {symbol}")

if __name__ == "__main__":
    submit_order("AAPL", 1, "buy")
