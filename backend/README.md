# Backend - Stock Prediction API

Flask REST API that provides stock price predictions for NSE (Indian market) stocks.

## Installation

1. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### POST /api/predict
Predict stock prices for a given ticker using Alpha Vantage history (TIME_SERIES_DAILY/WEEKLY/MONTHLY) and a lightweight ML model.

**Request:**
```json
{
  "ticker": "HFCL.BSE",
  "days": 3,
  "frequency": "monthly",
  "model": { "type": "ridge", "window": 180, "alpha": 1.0 }
}
```

**Response:**
```json
{
  "ticker": "RELIANCE",
  "predictions": [
    {"date": "2025-11-02", "price": 1234.56},
    {"date": "2025-11-03", "price": 1235.78}
  ],
  "error": null
}
```

Optional simulate mode (for offline tests only):

```json
{
  "ticker": "TCS",
  "days": 4,
  "mode": "simulate",
  "base_price": 1000,
  "drift_pct": 0.2,
  "vol_pct": 0.5,
  "slope": 2.0
}
```

Model params:
- model.type: "ridge" (default) or "rf" (RandomForestRegressor)
- model.window: lookback periods to train on (default: all available)
- model.alpha: Ridge regularization strength (only used for ridge)

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "message": "Stock Prediction API is running"
}
```

## Configuration and External Data Providers

The backend fetches historical prices strictly from Alpha Vantage’s:
- TIME_SERIES_DAILY
- TIME_SERIES_WEEKLY
- TIME_SERIES_MONTHLY

Supported provider and required environment variables:
- DATA_PROVIDER=alphavantage — requires ALPHA_VANTAGE_API_KEY

Example `.env` entries:
```
DATA_PROVIDER=alphavantage
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

If fetching history fails for the selected frequency, the API retries once with `monthly`. If still no data, it returns an error. A deterministic, API-only projection is used when ML cannot train (insufficient data).

Place a copy of `.env.example` as `.env` in the `backend/` folder or export the required env vars in your shell before running.