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

    # print("Fetching Reddit posts...")
    # hours = 72 if dt.datetime.now().weekday() == 0 else 24
    # raw_posts = fetch_recent_posts(hours=hours)

    # print(f"Fetched {len(raw_posts)} posts. Analyzing sentiment...")
    # analyzed = analyze_bulk(raw_posts)

    # print("Generating sentiment plot...")
    # plot_sentiment(analyzed)

    # print("Aggregating sentiments by ticker...")
    # ticker_data = aggregate_sentiments([post['text'] for post in raw_posts])

    # print("Generating trading signals...")
    # signals = generate_signals(ticker_data)

    # print("--- Trade Signals ---")
    # for ticker, signal in signals.items():
    #     print(f"{ticker}: {signal}")