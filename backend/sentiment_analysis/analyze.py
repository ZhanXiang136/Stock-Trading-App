from transformers import pipeline

# Load the FinBERT sentiment analysis model
sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")

def analyze_text(text: str):
    """
    Analyze sentiment of a single text input using FinBERT.
    Returns label ('positive', 'negative', or 'neutral') and confidence score.
    """
    result = sentiment_pipeline(text)[0]
    return {
        'label': result['label'].lower(),
        'score': round(result['score'], 4)
    }

def analyze_batch(texts):
    """
    Analyze a list of texts and return sentiment for each.
    """
    results = sentiment_pipeline(texts)
    return [
        {'text': t, 'label': r['label'].lower(), 'score': round(r['score'], 4)}
        for t, r in zip(texts, results)
    ]

if __name__ == "__main__":
    # Example: Single sentence
    text = "I'm all in on $GME. It's going to the moon"
    print(analyze_text(text))

    # Example: Batch of Reddit-style posts
    posts = [
        "Diamond hands on $AMC forever.",
        "$TSLA is way overvalued, shorting it now.",
        "Might hold $NVDA through earnings, not sure."
    ]
    for result in analyze_batch(posts):
        print(result)       