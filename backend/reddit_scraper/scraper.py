import praw
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent='WSB Sentiment App'
)

def fetch_recent_post_titles(limit=100):
    titles = []
    for post in reddit.subreddit('wallstreetbets').hot(limit=limit):
        if post.title:
            titles.append(post.title)
    return titles

if __name__ == "__main__":
    print(fetch_recent_post_titles())
