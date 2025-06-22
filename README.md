# 📈 Stock Trading App

This project leverages **natural language processing (NLP)** to analyze Reddit discussions from **r/WallStreetBets**, generating buy/sell signals based on **sentiment and ticker frequency**. It simulates trades and visualizes the bot's performance compared to popular indices like the **S&P 500** and **NASDAQ**.

---

## 🚀 Features

- 🔍 **Reddit Sentiment Analyzer** using a fine-tuned transformer model (ProsusAI/finbert)
- 📰 Real-time parsing of Reddit titles/posts for tickers and sentiment
- 📊 Trade simulation engine with PnL tracking
- 📈 Dashboard to visualize:
  - Bot equity over time
  - Comparison with S&P 500 / NASDAQ
  - Average sentiment trends per ticker
- 🧠 Transformer model fine-tuned on Reddit WSB data and Kaggle financial sentiment data

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, PRAW (Reddit API), Alpaca API
- **NLP Model:** ProsusAI/finbert (fine-tuned on custom data)
- **Frontend:** React.js + Recharts
- **Database/Storage:** Supabase / PostgreSQL (optional)
- **Visualization:** Matplotlib, Plotly, or Recharts

---

## 📂 Project Structure

```
src/
├── reddit_scraper/         # Scrapes r/wallstreetbets posts
├── sentiment_model/        # Finetuned transformer + preprocessing
├── trading_bot/            # Trade signal logic and equity simulator
├── performance_api/        # FastAPI backend to expose equity/performance
```

---

## ⚙️ Setup Instructions

1. **Clone the repo**

```bash
git clone https://github.com/yourusername/stock-trading-app.git
cd stock-trading-app
```

2. **Create `.env` file** (put in the root or appropriate folders)

```env
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=WSB Sentiment App

ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
cd dashboard && npm install
```

4. **Run backend and frontend**

```bash
# Backend
uvicorn src.main:app --reload

# Frontend (on seperate repo)
cd dashboard
npm run dev
```

---

## 📊 Example Output

- `/api/equity`: JSON of equity timeline
- `/api/sentiment`: Daily average sentiment per ticker
- `/dashboard`: Live dashboard with visual PnL and market comparison

---

## 📜 License & Dataset Credits

This project uses the **ProsusAI/finbert** model, fine-tuned with financial sentiment data from:

- **Charan Gowda**
- **Anirudh**
- **Akshay Pai**
- **Chaithanya Kumar A** *(dataset owner)*  
🔖 Dataset licensed under **Creative Commons License** (CC BY 4.0) via Kaggle.

---

## 🙌 Contributing

PRs are welcome! If you’d like to improve sentiment scoring, model training, or UI charts, feel free to open an issue or pull request.