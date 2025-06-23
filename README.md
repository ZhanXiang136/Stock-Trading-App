# 📈 AI-Powered Stock Trading App

This project uses **Natural Language Processing (NLP)** and real-time financial data to generate automated trading signals based on sentiment from Reddit’s stock trading subreddits [r/WallStreetBets, r/stock, etc]. It combines AI models with a web dashboard to visualize performance against market indices like the **S&P 500** and **NASDAQ**.

---

## 🚀 Features

- 🤖 **Sentiment Analysis**  
  Fine-tuned Hugging Face transformer model evaluates sentiment of Reddit posts mentioning stocks.

- 💬 **Smart Ticker Extraction**  
  Recognizes ticker symbols using `$` notation, fuzzy matching (e.g., “Tesla” → `$TSLA`), named entity recognition, and alias mapping.

- 📊 **Performance Visualization**  
  Frontend dashboard built with React.js to display:
  - Bot’s equity curve over time
  - Comparison with S&P 500 and NASDAQ
  - Last updated timestamp

- 🔁 **Automated Pipeline**  
  - Scrapes hot posts from WallStreetBets daily
  - Parses sentiment and tickers
  - Makes buy/sell decisions based on aggregated sentiment
  - Logs portfolio value for visualization

---

## 🧠 Tech Stack

- **Frontend**: React.js + Chart.js
- **Backend**: FastAPI + Python
- **ML Framework**: Hugging Face Transformers (`ProsusAI/finbert`)
- **Data Source**: Reddit API via PRAW
- **Broker API**: Alpaca API for real-time trading and equity tracking
- **Hosting**: Render / Netlify 

---

## 📂 Directory Structure

```
/src
│
├── reddit_sentiment_pipeline/
├──├── reddit_scraper/        # Scrapes Reddit posts
├──├── sentiment_model/       # Fine-tuned transformer model & tokenizer
├──├── ticker_extractor/      # Enhanced ticker name detection
├──├── fine_tune/             # Train/Test/Generate Financial model on Reddit lingo
├── trading_engine/           # Trading logic (buy/sell based on sentiment)
├── performance_api/          # FastAPI routes for frontend data
└── data/                     # Company alias + ticker mapping + dataset used
```

---

## ✅ Setup Instructions

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/yourusername/stock-trading-app.git
   cd stock-trading-app
   ```

2. **Create a virtual environment and install dependencies**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. **Set up environment variables**  
   Create a `.env` file in the root with your keys:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_secret
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ```

4. **Run the Backend API**  
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Start the Frontend**  
   Open up https://zhanxiangzheng.me/stocktradingai to view the progress history of you bot compared to other indexes
   At this time, the frontend will only run the api from http://127.0.0.1:8000/ so run your bot locally

---

## 👤 Acknowledgments

This app was trained using data from Kaggle, provided under the Creative Commons license by:

- Charan Gowda  
- Anirudh  
- Akshay Pai  
- Chaithanya Kumar A

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
