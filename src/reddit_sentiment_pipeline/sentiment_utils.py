import os

MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "src/model")

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

class Sentiment_Analyzer:
    def __init__(self):
        from src.reddit_sentiment_pipeline.ticket_extractor import EnhancedTickerExtractor
        from transformers import AutoTokenizer, pipeline

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.sentiment_model = pipeline("sentiment-analysis", model=MODEL_DIR, tokenizer=self.tokenizer)
        self.enhanced_extract_tickers= EnhancedTickerExtractor()



    def extract_tickers(self, text):
        return self.enhanced_extract_tickers.extract_from_text(text)

    def analyze_post(self, post):
        text = post['text']

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
            sentiment = post.get('sentiment', '').lower()
            score = float(post.get('score', 0) or 0)

            if sentiment not in {'positive', 'negative', 'neutral'}:
                continue

            for ticker in tickers:
                if ticker not in ticker_data:
                    ticker_data[ticker] = {
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0,
                        'mentions': 0,
                        'positive_score': 0.0,
                        'negative_score': 0.0,
                        'neutral_score': 0.0,
                    }
                ticker_data[ticker]['mentions'] += 1
                ticker_data[ticker][sentiment] += 1
                ticker_data[ticker][f'{sentiment}_score'] += score

        return ticker_data

    def generate_signals(
        self,
        ticker_data,
        threshold=None,
        mention_threshold=None,
        conflict_margin=None,
        volatility_sensitivity=None,
        min_threshold=None,
    ):
        threshold = threshold if threshold is not None else _env_float("SIGNAL_THRESHOLD", 0.6)
        mention_threshold = mention_threshold if mention_threshold is not None else _env_int("SIGNAL_MENTION_THRESHOLD", 3)
        conflict_margin = conflict_margin if conflict_margin is not None else _env_float("SIGNAL_CONFLICT_MARGIN", 0.2)
        volatility_sensitivity = (
            volatility_sensitivity
            if volatility_sensitivity is not None
            else _env_float("SIGNAL_VOLATILITY_SENSITIVITY", 0.05)
        )
        min_threshold = min_threshold if min_threshold is not None else _env_float("SIGNAL_MIN_THRESHOLD", 0.45)

        signals = {}
        for ticker, data in ticker_data.items():
            mentions = data.get('mentions', 0)
            if mentions < mention_threshold:
                signals[ticker] = 'HOLD'
                continue

            positive_weight = data.get('positive_score', 0.0)
            negative_weight = data.get('negative_score', 0.0)
            total_directional_weight = positive_weight + negative_weight

            if total_directional_weight == 0:
                signals[ticker] = 'HOLD'
                continue

            positive_ratio = positive_weight / total_directional_weight
            negative_ratio = negative_weight / total_directional_weight
            trading_threshold = self._volatility_adjusted_threshold(
                data.get('volatility'),
                base_threshold=threshold,
                sensitivity=volatility_sensitivity,
                min_threshold=min_threshold,
            )
            trading_conflict_margin = min(
                conflict_margin,
                max(0, (trading_threshold - 0.5) * 2),
            )

            if positive_ratio >= trading_threshold and positive_ratio - negative_ratio >= trading_conflict_margin:
                signals[ticker] = 'BUY'
            elif negative_ratio >= trading_threshold and negative_ratio - positive_ratio >= trading_conflict_margin:
                signals[ticker] = 'SELL'
            else:
                signals[ticker] = 'HOLD'
        return signals

    @staticmethod
    def _volatility_adjusted_threshold(
        volatility,
        base_threshold=0.6,
        sensitivity=0.05,
        min_threshold=0.45,
    ):
        if volatility is None:
            return base_threshold

        try:
            beta = float(volatility)
        except (TypeError, ValueError):
            return base_threshold

        if beta <= 1:
            return base_threshold

        return max(min_threshold, base_threshold - ((beta - 1) * sensitivity))

if __name__ == "__main__":
    sa = Sentiment_Analyzer()
