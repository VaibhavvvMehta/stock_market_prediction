# StockPrediction

Lightweight full-stack stock prediction app with a Flask backend (Alpha Vantage data) and a React frontend (Vite + Chart.js).

This repository fetches market data exclusively via Alpha Vantage non-adjusted endpoints (TIME_SERIES_DAILY/WEEKLY/MONTHLY and GLOBAL_QUOTE), computes technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV), and exposes prediction endpoints backed by a small ML pipeline (ridge / random forest fallback). The frontend provides tabs to view History, Quote, Indicators, and Predictions.

---

## Quickstart

Prerequisites
- Python 3.9+ (3.8 may work, but 3.9+ recommended)
- Node.js 16+ / npm
- An Alpha Vantage API key: https://www.alphavantage.co/support/#api-key

Important: Keep your API key private. Put it in a `.env` file (see below). Do NOT commit `.env` to the repository.

1) Clone the repo and create a GitHub repository (if you haven't already)

2) Backend setup (Windows PowerShell)

```powershell
cd "path\to\StockPrediction"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file in the project root with:

```text
ALPHA_VANTAGE_API_KEY=your_api_key_here
# optional: other env vars like FLASK_ENV=development
```

Run backend (from project root):

```powershell
# option A: run module directly
python .\backend\app.py

# option B: change into backend and run
cd .\backend
python app.py
```

The backend will listen on port 5000 by default.

3) Frontend setup

```powershell
cd .\frontend
npm install
# Dev server
npm run dev
# or build for production
npm run build
```

Open the frontend (Vite dev server) at the port shown (usually http://localhost:5173 or your configured port). The frontend talks to the backend at http://localhost:5000.

## What the repo contains
- `backend/` — Flask app and modules (`config.py`, `features.py`, `ml.py`, `app.py`)
- `frontend/` — Vite + React app (Chart.js) located under `frontend/`
- `requirements.txt` — Python dependencies for backend

## Git / GitHub push (Windows PowerShell)

1. Create a new empty repository on GitHub (e.g., `username/StockPrediction`).
2. From your local project root run:

```powershell
git init
git add .
git commit -m "Initial commit — StockPrediction"
# replace the remote url with your repo URL below
git remote add origin https://github.com/<your-username>/StockPrediction.git
git branch -M main
git push -u origin main
```

If you prefer SSH:

```powershell
git remote add origin git@github.com:<your-username>/StockPrediction.git
git push -u origin main
```

Notes
- `.gitignore` is configured to exclude virtual environments, `.env` files, `node_modules`, `dist`, IDE settings, and other common artifacts.
- If you plan to run multiple requests to Alpha Vantage, be mindful of free-tier rate limits. The frontend will surface a polite notice when a rate-limit response is detected.

## Contributing
- If you add features that require new environment variables, document them in this README and do not commit secrets.

## License
This project does not include a license file by default. Add an appropriate license (e.g., MIT) if you plan to publish it.

# Stock Price Prediction App

A full-stack web application for predicting Indian stock prices (NSE) with a Flask REST API backend and a React (Vite) frontend using Chart.js.

## Project Structure

- `backend/` — Flask API service
	- `app.py` — main Flask app (POST `/api/predict`, GET `/health`)
	- `config.py` — data provider config (Alpha Vantage API)
	- `requirements.txt` — backend dependencies
	- `tests/` — pytest tests for the API
- `frontend/` — React + Vite UI
	- `src/components/PredictionForm.jsx` — calls the API and renders the chart
	- `vite.config.js` — dev server config (port 3000)

## Run the Backend (PowerShell on Windows)

```powershell
cd "C:\Users\HP\Documents\Full Stack Projects\StockPrediction\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure data provider via .env
copy .env.example .env  # then edit values

python app.py
```

API will be available at http://localhost:5000.

Example request JSON body:

```json
{ "ticker": "RELIANCE", "days": 5 }
```

## Run the Frontend

```powershell
cd "C:\Users\HP\Documents\Full Stack Projects\StockPrediction\frontend"
npm install
npm run dev
```

App will be available at http://localhost:3000 and will call the backend at http://localhost:5000/api/predict.

## Data Providers and API keys

The backend fetches data strictly from Alpha Vantage. Set the following in `backend/.env`:

```
DATA_PROVIDER=alphavantage
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

See `backend/.env.example` and `backend/README.md` for details.

## Notes

- Auto mode uses API-fetched OHLCV and fundamentals to generate ML-based predictions (no local data fallbacks). Manual mode remains available when you supply a base price and parameters.
- CORS is configured to allow the Vite dev server (http://localhost:3000).
- Unit tests (pytest) cover health and predict endpoints. Run them with:

```powershell
cd .\backend
.\venv\Scripts\Activate.ps1
pytest -q
```

## Run with Docker (optional)

You can run both services with Docker Compose for a simple local deployment.

```powershell
cd "C:\Users\HP\Documents\Full Stack Projects\StockPrediction"
docker compose build
docker compose up -d
```

- Frontend: http://localhost:3000
- Backend: http://localhost:5000

To select a data provider and pass API keys:

```powershell
$env:DATA_PROVIDER = "alphavantage"
$env:ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_key_here"
docker compose up -d --build
```

Stop the stack:

```powershell
docker compose down
```
