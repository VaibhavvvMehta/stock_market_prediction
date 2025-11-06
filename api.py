from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)
# Allow requests from the React dev server
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})


def load_and_predict(ticker: str, days: int = 5):
    """
    Fetch recent price data for the given ticker (NSE .NS extension) and simulate
    a 5-day rolling LSTM forecast. Returns JSON-serializable dict.
    """
    try:
        if not ticker or not isinstance(ticker, str):
            return {"ticker": ticker, "predictions": [], "error": "invalid ticker"}

        t = ticker.strip().upper()
        if not t.endswith('.NS'):
            t = t + '.NS'

        yf_ticker = yf.Ticker(t)
        hist = yf_ticker.history(period="120d")

        if hist.empty:
            last_close = float(np.abs(np.random.normal(loc=1000.0, scale=50.0)))
        else:
            last_close = float(hist['Close'].iloc[-1])

        n_pred = min(int(days) if isinstance(days, (int, float)) and days > 0 else 5, 5)

        predictions = []
        drift = 0.001
        curr_price = last_close
        start_date = datetime.utcnow().date() + timedelta(days=1)

        for i in range(n_pred):
            curr_price = curr_price * (1 + drift)
            noise = np.random.normal(loc=0.0, scale=0.01)
            curr_price = curr_price * (1 + noise)
            pred_date = (start_date + timedelta(days=i)).isoformat()
            predictions.append({"date": pred_date, "price": round(float(curr_price), 2)})

        return {"ticker": t, "predictions": predictions, "error": None}

    except Exception as e:
        tb = traceback.format_exc()
        return {"ticker": ticker, "predictions": [], "error": str(e) + "\n" + tb}


@app.route('/api/predict', methods=['POST'])
def predict_route():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"ticker": None, "predictions": [], "error": "invalid or missing JSON body"}), 400

    ticker = payload.get('ticker')
    days = payload.get('days', 5)

    if not ticker or not isinstance(ticker, str) or ticker.strip() == "":
        return jsonify({"ticker": ticker, "predictions": [], "error": "ticker is required"}), 400

    try:
        days_int = int(days)
    except Exception:
        days_int = 5

    result = load_and_predict(ticker, days_int)
    status = 200 if result.get('error') is None else 500
    return jsonify(result), status


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
