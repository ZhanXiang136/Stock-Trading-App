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

def generate_signals(ticker_data, threshold=0.6, mention_threshold=10):
    signals = {}
    for ticker, data in ticker_data.items():
        sentiments = []
        total = data['mentions']

        for label in ['positive', 'negative']:
            sentiments.extend([{ 'label': label, 'score': 1.0 }] * data[label])  # assume full confidence if unavailable

        pos_scores = [s['score'] for s in sentiments if s['label'] == 'positive']
        neg_scores = [s['score'] for s in sentiments if s['label'] == 'negative']

        mention_count = len(sentiments)
        avg_pos = sum(pos_scores) / len(pos_scores) if pos_scores else 0
        avg_neg = sum(neg_scores) / len(neg_scores) if neg_scores else 0

        if mention_count >= mention_threshold:
            if avg_pos > threshold:
                signals[ticker] = 'BUY'
            elif avg_neg > threshold:
                signals[ticker] = 'SELL'
            else:
                signals[ticker] = 'HOLD'
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