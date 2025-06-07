import re
from transformers import pipeline

# Load Twitter-RoBERTa sentiment model
sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")

label_map = {
    'label_0': 'negative',
    'label_1': 'neutral',
    'label_2': 'positive'
}

def extract_tickers(text):
    return re.findall(r'\$[A-Z]{1,5}', text)

def analyze_sentiment(text, confidence_threshold=0.65):
    result = sentiment_pipeline(text)[0]
    label = label_map[result['label']]
    score = result['score']
    return (label, score) if score >= confidence_threshold else ('neutral', score)

def aggregate_sentiments(posts):
    ticker_data = {}

    for post in posts:
        tickers = extract_tickers(post)
        label, score = analyze_sentiment(post)

        for ticker in tickers:
            if ticker not in ticker_data:
                ticker_data[ticker] = {'positive': 0, 'negative': 0, 'neutral': 0, 'mentions': 0}
            ticker_data[ticker][label] += 1
            ticker_data[ticker]['mentions'] += 1

    return ticker_data

def generate_signals(ticker_data, threshold=0.6):
    signals = {}
    for ticker, data in ticker_data.items():
        total = data['mentions']
        pos_ratio = data['positive'] / total
        neg_ratio = data['negative'] / total

        if pos_ratio > threshold:
            signals[ticker] = 'BUY'
        elif neg_ratio > threshold:
            signals[ticker] = 'SELL'
        else:
            signals[ticker] = 'HOLD'
    return signals

if __name__ == "__main__":
    sample_posts = [
        "Diamond hands on $AMC forever.",
        "$TSLA is way overvalued, shorting it now.",
        "Might hold $NVDA through earnings, not sure.",
        "I'm going all in on $GME."
    ]
    aggregated = aggregate_sentiments(sample_posts)
    print("Aggregated Sentiment per Ticker:")
    print(aggregated)

    signals = generate_signals(aggregated)
    print("Generated Signals:")
    print(signals)
