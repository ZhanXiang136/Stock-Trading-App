import re
from transformers import pipeline
import os

class Sentiment_Analyzer:
    def __init__(self, model_path="./model"):
        self.model_path = model_path
        self.sentiment_model = pipeline("sentiment-analysis", model=self.model_path)
        #sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")


    def extract_tickers(self, text):
        return re.findall(r"\$[A-Z]{1,5}", text)

    def analyze_post(self, post):
        sentiment = self.sentiment_model(post['text'])[0]
        tickers = self.extract_tickers(post['text'])
        return {
            'text': post['text'],
            'tickers': tickers,
            'sentiment': sentiment['label'],
            'score': sentiment['score'],
            'timestamp': post['timestamp']
        }

    def analyze_bulk(self, posts):
        return [self.analyze_post(post) for post in posts]



    def aggregate_sentiments(self, posts):
        ticker_data = {}

        for post in posts:
            tickers = self.extract_tickers(post['text'])
            sentiment = self.sentiment_model(post['text'])[0]
            label = sentiment['label']
            score = sentiment['score']

            for ticker in tickers:
                if ticker not in ticker_data:
                    ticker_data[ticker] = {'positive': 0, 'negative': 0, 'neutral': 0, 'mentions': 0}
                ticker_data[ticker][label] += 1
                ticker_data[ticker]['mentions'] += 1

        return ticker_data

    def generate_signals(self, ticker_data, threshold=0.6, mention_threshold=10):
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
