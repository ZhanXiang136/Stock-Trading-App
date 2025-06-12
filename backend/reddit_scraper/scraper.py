import praw
import os
import datetime as dt
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
                'comments': comments
            })

    return recent_posts

def fetch_recent_posts(limit: int = 1000):
    """
    Fetch recent posts from the WallStreetBets subreddit.
    :param limit: Maximum number of posts to fetch
    :return: List of recent posts with their details
    """
    hours = 72 if dt.datetime.now().weekday == 0 else 24
    return fetch_recent_posts(hours, limit=limit)


if __name__ == "__main__":
    print(fetch_recent_posts(1)[0])
