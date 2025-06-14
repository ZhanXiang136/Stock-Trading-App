"""
This module labels text data with weak sentiment labels using VADER sentiment analysis.
# It reads raw data from a JSON file, processes each text entry to determine its sentiment,
# and writes the labeled data to a new JSON file.
"""

import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def label_text(text):
    score = analyzer.polarity_scores(text)['compound']
    if score >= 0.3:
        return "positive"
    elif score <= -0.3:
        return "negative"
    else:
        return "neutral"

def label_dataset(raw_data_path, output_path):
    with open(raw_data_path, 'r') as f:
        data = json.load(f)

    labeled = []
    for item in data:
        label = label_text(item['text'])
        labeled.append({"text": item['text'], "label": label})

    with open(output_path, 'w') as f:
        json.dump(labeled, f, indent=2)