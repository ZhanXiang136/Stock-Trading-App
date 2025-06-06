import praw
import os

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent='WSB Sentiment App'
)

def fetch_posts(limit=100):
    posts = []
    for post in reddit.subreddit('wallstreetbets').hot(limit=limit):
        if post.title:
            posts.append({
                'id': post.id,
                'title': post.title,
                'score': post.score,
                'created': post.created_utc,
                'url': post.url,
                'num_comments': post.num_comments
            })
    return posts

if __name__ == "__main__":
    from pprint import pprint
    data = fetch_posts()
    pprint(data[:5])