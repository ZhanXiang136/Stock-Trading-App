# 📈 Trading Bot Performance API

This is a FastAPI backend that powers a trading bot performance dashboard. It tracks your bot's equity via Alpaca and compares it with 30-day returns of the S&P 500 and NASDAQ using Yahoo Finance.

---

## 🚀 Features

- Fetches real-time bot equity from Alpaca
- Pulls 30-day S&P 500 and NASDAQ performance
- Calculates cumulative % returns
- Exposes `/api/performance` endpoint
- Supports cross-origin requests for frontend consumption

---

## 📦 Tech Stack

- FastAPI
- Alpaca Trade API
- yFinance
- Python 3.10+
- Uvicorn

---
