import praw
import os
import datetime as dt
import time
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

def get_volatility(ticker_symbol):
    """
    Args: a single ticker symbol (str), or a list of symbols (list)
    Returns: A dictionary mapping the symbol to its beta value.
    """
    if not isinstance(ticker_symbol, list):
        ticker_symbol = [ticker_symbol]
    
    ticker_symbol = list(set([sym.upper() for sym in ticker_symbol]))
    filename = DATA_DIR / "volatility.csv"
    og_size = len(ticker_symbol)
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
    
    with open(filename, 'r') as f: 
        reader = csv.reader(f)
        for row in reader: 
            if len(row) == 2: 
                symbol, beta = row
                if str(symbol) in ticker_symbol: 
                    beta_values[symbol] = float(beta) if beta != "None" else None
                    ticker_symbol.remove(str(symbol))      

    if len(beta_values) == og_size: 
        return beta_values
    with open(filename, 'a+') as f: 
        for symbol in ticker_symbol: 
            try: 
                ticker = yf.Ticker(symbol)
                beta = ticker.info.get("beta")
                beta_values[symbol] = beta
                print(f"Fetched beta for {symbol}")
            except Exception as e: 
                print(f"Failed {symbol}: {e}")
                beta = None
                beta_values[symbol] = beta

            f.write(f"{symbol},{beta}\n")
            time.sleep(1)
    
    return beta_values

if __name__ == "__main__":
    print(fetch_recent_posts(24, 2)[0])
