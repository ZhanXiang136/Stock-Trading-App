import praw
import os
import datetime as dt
import csv
import yfinance as yf
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent='WSB Sentiment App'
)

UTC = ZoneInfo("UTC")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def is_within_timeframe(created_utc: float, hours: int):
    """
    Check if the post was created within the last 'hours' hours.
    :param created_utc: Post creation time in UTC timestamp
    :param hours: Number of hours to check against
    :return: True if post is within the timeframe, False otherwise
    """
    post_time = dt.datetime.fromtimestamp(created_utc, tz=UTC)
    time_limit = dt.datetime.now(tz=UTC) - dt.timedelta(hours=hours)
    return post_time >= time_limit

def fetch_recent_posts(hours: int = 24, limit: int = 1000):
    """
    Fetch recent posts from the WallStreetBets subreddit.
    :param hours: Timeframe in hours to filter posts
    :param limit: Maximum number of posts to fetch
    :return: List of recent posts with their details
    """
    subreddit = reddit.subreddit('wallstreetbets')
    recent_posts = []

    for post in subreddit.new(limit=limit):
        if is_within_timeframe(post.created_utc, hours):
            post.comments.replace_more(limit=0)
            comments = [comment.body for comment in post.comments.list()]
            downvotes = post.ups - post.score  # Estimated dislikes
            recent_posts.append({
                'title': post.title,
                'body': post.selftext,
                'upvotes': post.ups,
                'downvotes': downvotes,
                'score': post.score,
                'comments': comments,
                'timestamp': post.created_utc,
            })

    return recent_posts

def _calculate_beta_from_returns(returns, symbol, benchmark):
    if symbol == benchmark:
        return 1.0
    if symbol not in returns or benchmark not in returns:
        return None

    aligned = returns[[symbol, benchmark]].dropna()
    if len(aligned) < 2:
        return None

    benchmark_variance = aligned[benchmark].var()
    if not benchmark_variance or benchmark_variance <= 0:
        return None

    return aligned[symbol].cov(aligned[benchmark]) / benchmark_variance

def _fetch_alpaca_betas(symbols, benchmark):
    import pandas as pd
    from alpaca_trade_api.rest import TimeFrame
    from src.trading_engine.alpaca_trade import get_alpaca_api

    symbol_map = {symbol: symbol.replace("-", ".") for symbol in symbols}
    days = int(os.getenv("VOLATILITY_LOOKBACK_DAYS", "180"))
    start = (dt.datetime.now(tz=UTC) - dt.timedelta(days=days)).date().isoformat()
    feed = os.getenv("ALPACA_DATA_FEED", "iex").strip() or "iex"
    api = get_alpaca_api()
    betas = {}

    def close_prices_from_bars(bars_df, fallback_symbol):
        if bars_df.empty:
            return None

        if "symbol" in bars_df.columns:
            return bars_df.pivot_table(
                index=bars_df.index,
                columns="symbol",
                values="close",
                aggfunc="last",
            )

        if isinstance(bars_df.index, pd.MultiIndex):
            for level in range(bars_df.index.nlevels):
                values = set(str(value) for value in bars_df.index.get_level_values(level).unique())
                if fallback_symbol in values or benchmark in values:
                    return bars_df["close"].unstack(level=level)

        return bars_df[["close"]].rename(columns={"close": fallback_symbol})

    for symbol, alpaca_symbol in symbol_map.items():
        if symbol == benchmark:
            betas[symbol] = 1.0
            continue

        try:
            bars = api.get_bars(
                sorted({alpaca_symbol, benchmark}),
                TimeFrame.Day,
                start=start,
                adjustment="all",
                feed=feed,
            )
            bars_df = bars.df
            close_prices = close_prices_from_bars(bars_df, alpaca_symbol)
            if close_prices is None:
                continue

            close_prices = close_prices.rename(columns={alpaca_symbol: symbol})
            returns = close_prices.pct_change().dropna(how="all")
            beta = _calculate_beta_from_returns(returns, symbol, benchmark)
            if beta is not None:
                betas[symbol] = round(float(beta), 4)
        except Exception as e:
            print(f"Failed Alpaca beta for {symbol}: {e}")

    return betas

def _fetch_yfinance_betas(symbols, benchmark):
    download_symbols = sorted(set(symbols + [benchmark]))
    lookback = os.getenv("VOLATILITY_LOOKBACK", "6mo")
    price_data = yf.download(
        download_symbols,
        period=lookback,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    close_prices = price_data["Close"] if "Close" in price_data else price_data
    returns = close_prices.pct_change().dropna(how="all")

    betas = {}
    for symbol in symbols:
        beta = _calculate_beta_from_returns(returns, symbol, benchmark)
        if beta is not None:
            betas[symbol] = round(float(beta), 4)
    return betas

def get_volatility(ticker_symbol):
    """
    Args: a single ticker symbol (str), or a list of symbols (list)
    Returns: A dictionary mapping the symbol to its beta value.
    """
    if not isinstance(ticker_symbol, list):
        ticker_symbol = [ticker_symbol]
    
    ticker_symbol = sorted(set([sym.upper() for sym in ticker_symbol if sym]))
    filename = DATA_DIR / "volatility.csv"
    beta_values = {}
    remove = False

    if os.path.exists(filename): 
        with open(filename, 'r') as f: 
            fline = f.readline().strip()
            try: 
                creation_date = dt.date.fromisoformat(fline)
                if creation_date < dt.date.today(): 
                    remove = True
            except ValueError: 
                remove = True

    if remove: 
        os.remove(filename)
        print("outdated volatility file, delete and remake")  

    if not os.path.exists(filename): 
        with open(filename, 'w') as f:
            f.write(f'{dt.date.today().isoformat()}\n')
    
    missing_symbols = ticker_symbol.copy()
    with open(filename, 'r') as f: 
        reader = csv.reader(f)
        for row in reader: 
            if len(row) == 2: 
                symbol, beta = row
                symbol = str(symbol).upper()
                if symbol in missing_symbols and beta not in {"", "None"}:
                    beta_values[symbol] = float(beta)
                    missing_symbols.remove(symbol)      

    if not missing_symbols: 
        return beta_values

    benchmark = "SPY"
    fetched_betas = {}

    try:
        fetched_betas = _fetch_alpaca_betas(missing_symbols, benchmark)
    except Exception as e:
        print(f"Failed Alpaca volatility fetch: {e}")

    still_missing = [symbol for symbol in missing_symbols if symbol not in fetched_betas]
    if still_missing:
        try:
            fetched_betas.update(_fetch_yfinance_betas(still_missing, benchmark))
        except Exception as e:
            print(f"Failed Yahoo volatility fetch: {e}")

    for symbol in missing_symbols:
        beta = fetched_betas.get(symbol)
        if beta is not None:
            print(f"Fetched beta for {symbol}: {beta}")
        else:
            print(f"Failed {symbol}: beta unavailable")
        beta_values[symbol] = beta

    with open(filename, 'w') as f:
        f.write(f'{dt.date.today().isoformat()}\n')
        for symbol in sorted(beta_values):
            beta = beta_values[symbol]
            if beta is not None:
                f.write(f"{symbol},{beta}\n")
    
    return beta_values

if __name__ == "__main__":
    print(fetch_recent_posts(24, 2)[0])
