# Stock-Trading-App

This project analyzes Reddit posts from `r/wallstreetbets` to generate buy/sell stock signals using semantic sentiment analysis.

## Modules
- `scraper.py` – collects Reddit posts using the PRAW API
- `analyze.py` – uses FinBERT for sentiment classification

## Setup

1. Install dependencies:
   ```bash
   pip install praw transformers torch