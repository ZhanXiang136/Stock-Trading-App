import pandas as pd
import matplotlib.pyplot as plt

def plot_sentiment(posts):
    df = pd.DataFrame(posts)
    df = df.explode('tickers')
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["sentiment_score"] = df["score"].where(df["sentiment"] == "positive", -df["score"])

    avg_sentiment = df.groupby([df.timestamp.dt.date, "tickers"])["sentiment_score"].mean().unstack()

    avg_sentiment.plot(title="Average Sentiment Over Time", figsize=(10, 5))
    plt.ylabel("Avg Sentiment Score")
    plt.xlabel("Date")
    plt.grid(True)
    plt.tight_layout()
    plt.show()