from transformers import pipeline

# Load FinBERT model from HuggingFace
sentiment_model = pipeline("sentiment-analysis", model="ProsusAI/finbert")

def analyze_sentiment(text):
    result = sentiment_model(text)
    return result[0] if result else {'label': 'neutral', 'score': 0.0}

if __name__ == "__main__":
    sample = "I'm going all in on $GME, it's a no-brainer!"
    print(analyze_sentiment(sample))