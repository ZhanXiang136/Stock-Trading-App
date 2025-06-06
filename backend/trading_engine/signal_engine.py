import statistics

def generate_signal(sentiments, threshold=0.6, mention_threshold=10):
    '''
    sentiments: list of dicts like [{'label': 'positive', 'score': 0.85}, ...]
    Returns 'BUY', 'SELL', or 'HOLD'
    '''
    if not sentiments:
        return 'HOLD'

    pos_scores = [s['score'] for s in sentiments if s['label'] == 'positive']
    neg_scores = [s['score'] for s in sentiments if s['label'] == 'negative']

    mention_count = len(sentiments)
    avg_pos = statistics.mean(pos_scores) if pos_scores else 0
    avg_neg = statistics.mean(neg_scores) if neg_scores else 0

    if mention_count >= mention_threshold:
        if avg_pos > threshold:
            return 'BUY'
        elif avg_neg > threshold:
            return 'SELL'
    return 'HOLD'
if __name__ == "__main__":
    sample_sentiments = [{'label': 'positive', 'score': 0.75}] * 20
    print(generate_signal(sample_sentiments))  # Expected: BUY
