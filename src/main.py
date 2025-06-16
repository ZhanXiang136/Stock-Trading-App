import os
import datetime as dt
from reddit_sentiment_pipeline.scrape import fetch_recent_posts
from reddit_sentiment_pipeline.sentiment_utils import Sentiment_Analyzer
from reddit_sentiment_pipeline.visualize import plot_sentiment
from reddit_sentiment_pipeline.fine_tune import fine_tune_from_csv

MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "./model")
TRAIN_CSV = os.getenv("TRAIN_CSV", "./data/Reddit_Data.csv")

def ensure_model_trained():
    if not os.path.exists(MODEL_DIR):
        print("Model not found. Fine-tuning model using training data...")
        fine_tune_from_csv(TRAIN_CSV)
    else:
        print(f"Using existing model at: {MODEL_DIR}")

if __name__ == "__main__":
    ensure_model_trained()

    print("Fetching Reddit posts...")
    hours = 72 if dt.datetime.now().weekday() == 0 else 24
    raw_posts = fetch_recent_posts(hours=hours)

    for post in raw_posts:
        title = post.get("title", "")
        body = post.get("body", "")
        comments = post.get("comments", [])
        comment_text = " ".join(comments[:3]) 
        full_text = f"{title} {body} {comment_text}".strip()
        post['text'] = full_text

    sentiment_analyzer = Sentiment_Analyzer(model_path=MODEL_DIR)

    print(f"Fetched {len(raw_posts)} posts. Analyzing sentiment...")
    analyzed = sentiment_analyzer.analyze_bulk(raw_posts)
    print(analyzed[:5])  # Print first 5 analyzed posts for debugging

    # print("Generating sentiment plot...")
    # plot_sentiment(analyzed)

    print("Aggregating sentiments by ticker...")
    ticker_data = sentiment_analyzer.aggregate_sentiments(analyzed)

    print("Generating trading signals...")
    signals = sentiment_analyzer.generate_signals(ticker_data)

    print("--- Trade Signals ---")
    for ticker, signal in signals.items():
        print(f"{ticker}: {signal}")