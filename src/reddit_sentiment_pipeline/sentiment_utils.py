# src/reddit_sentiment_pipeline/sentiment_utils.py

class Sentiment_Analyzer:
    def __init__(self, model_path="./model"):
        from transformers import pipeline, AutoTokenizer
        from src.reddit_sentiment_pipeline.ticket_extractor import EnhancedTickerExtractor
        
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.sentiment_model = pipeline("sentiment-analysis", model=self.model_path, tokenizer=self.tokenizer)
        #sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
        self.enhanced_extract_tickers= EnhancedTickerExtractor()



    def extract_tickers(self, text):
        return self.enhanced_extract_tickers.extract_from_text(text)

    def analyze_post(self, post):
        text = post['text']

        # Truncate safely if text is too long
        encoded = self.tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
        decoded = self.tokenizer.decode(encoded['input_ids'][0], skip_special_tokens=True)

        sentiment = self.sentiment_model(decoded)[0]
        tickers = self.extract_tickers(text)
        return {
            'text': text,
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
            if 'tickers' not in post:
                continue
            tickers = post['tickers']
            sentiment = post['sentiment']
            # label = sentiment['label']
            # score = sentiment['score']

            for ticker in tickers:
                if ticker not in ticker_data:
                    ticker_data[ticker] = {'positive': 0, 'negative': 0, 'neutral': 0, 'mentions': 0}
                # ticker_data[ticker][label] += 1
                ticker_data[ticker]['mentions'] += 1

        return ticker_data

    def generate_signals(self, ticker_data, threshold=0.6, mention_threshold=1):
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
    sa = Sentiment_Analyzer()