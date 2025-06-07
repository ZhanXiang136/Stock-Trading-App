from backend.reddit_scraper.scraper import fetch_recent_post_titles
from backend.sentiment_analysis.sentiment_signal import aggregate_sentiments, generate_signals
from backend.trading_engine.alpaca_trade import submit_order
import os

def main():
    print("🔄 Fetching Reddit posts...")
    posts = fetch_recent_post_titles(limit=50)

    print("🧠 Analyzing sentiments...")
    sentiment_data = aggregate_sentiments(posts)

    print("📈 Generating trading signals...")
    signals = generate_signals(sentiment_data)

    for ticker, action in signals.items():
        if action in ['BUY', 'SELL']:
            print(f"🚀 Executing trade: {action} {ticker}")
            # Strip the $ before placing order
            submit_order(ticker[1:], 1, side=action.lower())
        else:
            print(f"⏸️ Holding position on {ticker}")

if __name__ == "__main__":
    main()
