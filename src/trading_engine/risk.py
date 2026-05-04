import os
from dataclasses import dataclass

from src.trading_engine.alpaca_trade import get_alpaca_api, get_position
from src.trading_engine.trade_log import count_submitted_trades_today

@dataclass
class RiskDecision:
    allowed: bool
    reason: str

def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}

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

def get_latest_price(symbol: str) -> float | None:
    feed = os.getenv("ALPACA_DATA_FEED", "iex").strip() or "iex"

    try:
        trade = get_alpaca_api().get_latest_trade(symbol, feed=feed)
        price = getattr(trade, "p", None)
        if price:
            return float(price)
    except Exception as exc:
        print(f"Failed to fetch latest Alpaca trade for {symbol}: {exc}")

    try:
        quote = get_alpaca_api().get_latest_quote(symbol, feed=feed)
        bid_price = float(getattr(quote, "bp", 0) or 0)
        ask_price = float(getattr(quote, "ap", 0) or 0)
        if bid_price and ask_price:
            return (bid_price + ask_price) / 2
        if ask_price:
            return ask_price
        if bid_price:
            return bid_price
    except Exception as exc:
        print(f"Failed to fetch latest Alpaca quote for {symbol}: {exc}")

    try:
        asset = get_alpaca_api().get_asset(symbol)
        if not getattr(asset, "tradable", False):
            print(f"{symbol} is not tradable on Alpaca.")
    except Exception:
        pass

    return None

def is_market_open() -> bool:
    try:
        return bool(get_alpaca_api().get_clock().is_open)
    except Exception as exc:
        print(f"Failed to check Alpaca market clock: {exc}")
        return False

def evaluate_trade_risk(symbol: str, qty: int, side: str) -> RiskDecision:
    if side not in {"buy", "sell"}:
        return RiskDecision(False, "unsupported side")

    if _env_bool("ENFORCE_MARKET_HOURS", True) and not is_market_open():
        return RiskDecision(False, "market is closed")

    max_daily_trades = _env_int("MAX_DAILY_TRADES", 10)
    if count_submitted_trades_today() >= max_daily_trades:
        return RiskDecision(False, "daily trade limit reached")

    position = get_position(symbol)
    if side == "buy" and position is not None:
        return RiskDecision(False, "already holding position")

    if side == "sell" and position is None:
        return RiskDecision(False, "no position to sell")

    if side == "buy":
        price = get_latest_price(symbol)
        if price is None:
            return RiskDecision(False, "latest price unavailable")

        max_position_value = _env_float("MAX_POSITION_VALUE", 1000.0)
        order_value = price * qty
        if order_value > max_position_value:
            return RiskDecision(False, f"order value {order_value:.2f} exceeds max {max_position_value:.2f}")

    return RiskDecision(True, "risk checks passed")
