from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import traceback
import logging
import os
from importlib.machinery import SourceFileLoader

# Robustly import fetch functions from config.py whether run as script or package
try:
    # package-style
    from .config import fetch_history, fetch_fundamentals_av, fetch_global_quote_av
except Exception:
    try:
        # script/module in same folder
        import config  # type: ignore
        fetch_history = config.fetch_history  # type: ignore[attr-defined]
        fetch_fundamentals_av = config.fetch_fundamentals_av  # type: ignore[attr-defined]
        fetch_global_quote_av = config.fetch_global_quote_av  # type: ignore[attr-defined]
    except Exception:
        try:
            # direct load from file path
            _cfg_path = os.path.join(os.path.dirname(__file__), 'config.py')
            _config = SourceFileLoader('config', _cfg_path).load_module()  # type: ignore[deprecated]
            fetch_history = _config.fetch_history  # type: ignore[attr-defined]
            fetch_fundamentals_av = _config.fetch_fundamentals_av  # type: ignore[attr-defined]
            fetch_global_quote_av = _config.fetch_global_quote_av  # type: ignore[attr-defined]
        except Exception:
            # last resort: define a stub to avoid signature mismatch
            def fetch_history(ticker, period='120d', frequency='daily', outputsize='compact', return_metadata=False, api_key=None):
                raise RuntimeError('config.fetch_history is not available')
            def fetch_fundamentals_av(ticker):
                return {}
            def fetch_global_quote_av(ticker):
                return {"error": "config.fetch_global_quote_av is not available"}

# Import indicators computation
try:
    from .features import compute_technical_indicators
except Exception:
    try:
        import features  # type: ignore
        compute_technical_indicators = features.compute_technical_indicators  # type: ignore[attr-defined]
    except Exception:
        _feat_path = os.path.join(os.path.dirname(__file__), 'features.py')
        _feat = SourceFileLoader('features', _feat_path).load_module()  # type: ignore[deprecated]
        compute_technical_indicators = _feat.compute_technical_indicators  # type: ignore[attr-defined]

# Try to import ML forecaster
try:
    from .ml import train_and_predict_ml
except Exception:
    try:
        import ml  # type: ignore
        train_and_predict_ml = ml.train_and_predict_ml  # type: ignore[attr-defined]
    except Exception:
        # final attempt: load from same folder path
        try:
            _ml_path = os.path.join(os.path.dirname(__file__), 'ml.py')
            _ml = SourceFileLoader('ml', _ml_path).load_module()  # type: ignore[deprecated]
            train_and_predict_ml = _ml.train_and_predict_ml  # type: ignore[attr-defined]
        except Exception:
            def train_and_predict_ml(df, fundamentals, steps=5):
                raise RuntimeError('ml.train_and_predict_ml is not available')

LOG = logging.getLogger(__name__)

app = Flask(__name__)
# Allow requests from the React dev server
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:5173"]}})


def load_and_predict(ticker: str, days: int = 5, manual: dict = None, frequency: str = 'daily'):
    """
    Fetch recent price data for the given ticker using configured provider and
    simulate a short forecast. Returns JSON-serializable dict.
    """
    try:
        if not ticker or not isinstance(ticker, str):
            return {"ticker": ticker, "predictions": [], "error": "invalid ticker"}

        t = ticker.strip().upper()
        raw_ticker = t  # keep raw symbol (REL/BSE/NS)

        # Manual mode: user-supplied parameters
        n_pred = min(int(days) if isinstance(days, (int, float)) and days > 0 else 5, 5)

        # capture request-scoped model/api params
        mp = app.config.get('_MODEL_PARAMS', {}) if hasattr(app, 'config') else {}
        api_key = mp.get('api_key') if isinstance(mp, dict) else None
        market_ticker = mp.get('market_ticker') if isinstance(mp, dict) else None

        ind_latest = None

        if manual:
            # Base price
            base_price = manual.get('base_price')
            try:
                base_price = float(base_price) if base_price is not None else None
            except Exception:
                base_price = None

            # choose starting price
            if base_price is None:
                # fall back to provider history if available, else a safe default
                try:
                    hist = fetch_history(raw_ticker, period='120d', frequency=frequency, outputsize='full', api_key=api_key)
                except Exception:
                    LOG.exception('fetch_history failed for %s', raw_ticker)
                    hist = pd.DataFrame()

                if hist is None or hist.empty:
                    # Try a fallback frequency (monthly) once, since some tickers respond only on monthly
                    if frequency != 'monthly':
                        try:
                            hist = fetch_history(raw_ticker, period='120d', frequency='monthly', outputsize='full', api_key=api_key)
                        except Exception:
                            LOG.exception('fallback monthly fetch_history failed for %s', raw_ticker)
                            hist = pd.DataFrame()
                if hist is None or hist.empty:
                    return {"ticker": raw_ticker, "predictions": [], "error": "no history available from provider; provide base_price or try later"}
                else:
                    # compute latest indicators snapshot for UI
                    try:
                        inds = compute_technical_indicators(hist)
                        last = inds.iloc[-1]
                        def _g(name):
                            try:
                                v = last[name]
                                return None if pd.isna(v) else float(v)
                            except Exception:
                                return None
                        ind_latest = {
                            'date': (inds.index[-1].isoformat() if hasattr(inds.index[-1], 'isoformat') else str(inds.index[-1])),
                            'close': float(last['close']) if 'close' in inds.columns and pd.notna(last['close']) else None,
                            'sma_20': _g('sma_20'),
                            'ema_20': _g('ema_20'),
                            'rsi_14': _g('rsi_14'),
                            'macd': _g('macd'),
                            'macd_signal': _g('macd_signal'),
                            'macd_hist': _g('macd_hist'),
                            'bb_mid': _g('bb_mid'),
                            'bb_upper': _g('bb_upper'),
                            'bb_lower': _g('bb_lower'),
                            'atr_14': _g('atr_14'),
                            'obv': _g('obv') if 'obv' in inds.columns else None,
                        }
                    except Exception:
                        ind_latest = None
                    if 'close' in hist.columns:
                        last_close = float(hist['close'].iloc[-1])
                    elif 'Close' in hist.columns:
                        last_close = float(hist['Close'].iloc[-1])
                    else:
                        numeric_cols = hist.select_dtypes('number').columns
                        if len(numeric_cols):
                            last_close = float(hist[numeric_cols[0]].iloc[-1])
                        else:
                            return {"ticker": raw_ticker, "predictions": [], "error": "unable to determine last close from provider data"}
            else:
                last_close = base_price

            # Manual simulation parameters
            try:
                drift = float(manual.get('drift_pct') or 0.1) / 100.0
            except Exception:
                drift = 0.001
            try:
                vol = float(manual.get('vol_pct') or 1.0) / 100.0
            except Exception:
                vol = 0.01
            try:
                slope_add = float(manual.get('slope') or 0.0)
            except Exception:
                slope_add = 0.0

            # Build manual predictions
            predictions = []
            curr_price = last_close
            step_days = 1 if frequency == 'daily' else (7 if frequency == 'weekly' else 30)
            start_date = datetime.utcnow().date() + timedelta(days=step_days)
            for i in range(n_pred):
                curr_price = curr_price * (1 + drift)
                curr_price = curr_price + slope_add
                noise = np.random.normal(loc=0.0, scale=vol)
                curr_price = curr_price * (1 + noise)
                pred_date = (start_date + timedelta(days=i * step_days)).isoformat()
                predictions.append({"date": pred_date, "price": round(float(curr_price), 2)})

        else:
            # Auto mode: fetch history via configured provider
            try:
                hist = fetch_history(raw_ticker, period='120d', frequency=frequency, outputsize='full', api_key=api_key)
            except Exception:
                LOG.exception('fetch_history failed for %s', raw_ticker)
                hist = pd.DataFrame()

            if hist is None or hist.empty:
                # Fallback to monthly once if initial frequency fails
                if frequency != 'monthly':
                    try:
                        hist = fetch_history(raw_ticker, period='120d', frequency='monthly', outputsize='full', api_key=api_key)
                    except Exception:
                        LOG.exception('fallback monthly fetch_history failed for %s', raw_ticker)
                        hist = pd.DataFrame()
            if hist is None or hist.empty:
                return {"ticker": raw_ticker, "predictions": [], "error": "no history available from provider"}

            # compute latest indicators snapshot for UI
            try:
                inds = compute_technical_indicators(hist)
                last = inds.iloc[-1]
                def _g(name):
                    try:
                        v = last[name]
                        return None if pd.isna(v) else float(v)
                    except Exception:
                        return None
                ind_latest = {
                    'date': (inds.index[-1].isoformat() if hasattr(inds.index[-1], 'isoformat') else str(inds.index[-1])),
                    'close': float(last['close']) if 'close' in inds.columns and pd.notna(last['close']) else None,
                    'sma_20': _g('sma_20'),
                    'ema_20': _g('ema_20'),
                    'rsi_14': _g('rsi_14'),
                    'macd': _g('macd'),
                    'macd_signal': _g('macd_signal'),
                    'macd_hist': _g('macd_hist'),
                    'bb_mid': _g('bb_mid'),
                    'bb_upper': _g('bb_upper'),
                    'bb_lower': _g('bb_lower'),
                    'atr_14': _g('atr_14'),
                    'obv': _g('obv') if 'obv' in inds.columns else None,
                }
            except Exception:
                ind_latest = None

            # Fetch fundamentals (Alpha Vantage OVERVIEW) if available
            try:
                fundamentals = fetch_fundamentals_av(raw_ticker, api_key=api_key) or {}
            except Exception:
                LOG.exception('fetch_fundamentals_av failed for %s', raw_ticker)
                fundamentals = {}

            # Optional market index correlation: fetch market_ticker history and attach market_close series
            if market_ticker:
                try:
                    m_hist = fetch_history(market_ticker.strip().upper(), period='120d', frequency=frequency, outputsize='full', api_key=api_key)
                    if m_hist is not None and not m_hist.empty:
                        fundamentals['market_close'] = m_hist['close'].astype(float) if 'close' in m_hist.columns else None
                except Exception:
                    LOG.exception('fetch_history for market_ticker failed: %s', market_ticker)

            # Use ML-based predictions relying solely on provider data; if ML unavailable/insufficient, fall back to deterministic drift from API data
            try:
                mp = app.config.get('_MODEL_PARAMS', {})
                prices = train_and_predict_ml(
                    hist,
                    fundamentals,
                    steps=n_pred,
                    model_type=(mp.get('model_type') or 'ridge'),
                    window=mp.get('window'),
                    ridge_alpha=float(mp.get('ridge_alpha') or 1.0),
                )
            except Exception:
                # Deterministic fallback: use average log-return over last K periods (API-only data)
                ser = None
                if 'close' in hist.columns:
                    ser = hist['close'].astype(float)
                elif 'Close' in hist.columns:
                    ser = hist['Close'].astype(float)
                else:
                    num_cols = hist.select_dtypes('number').columns
                    if len(num_cols):
                        ser = hist[num_cols[0]].astype(float)
                if ser is None or ser.shape[0] < 5:
                    return {"ticker": raw_ticker, "predictions": [], "error": "insufficient history returned from provider"}
                log_rets = np.log(ser / ser.shift(1)).dropna()
                if log_rets.empty:
                    return {"ticker": raw_ticker, "predictions": [], "error": "insufficient history to compute returns"}
                K = int(min(20, len(log_rets)))
                mean_r = float(log_rets.tail(K).mean())
                last_close = float(ser.iloc[-1])
                prices = []
                curr = last_close
                for _ in range(n_pred):
                    curr = curr * float(np.exp(mean_r))
                    prices.append(curr)

            # Build date series according to frequency
            step_days = 1 if frequency == 'daily' else (7 if frequency == 'weekly' else 30)
            start_date = datetime.utcnow().date() + timedelta(days=step_days)
            predictions = []
            for i, p in enumerate(prices):
                pred_date = (start_date + timedelta(days=i * step_days)).isoformat()
                predictions.append({"date": pred_date, "price": round(float(p), 2)})

        # Keep user-entered symbol as-is
        output_ticker = t
        return {"ticker": output_ticker, "predictions": predictions, "indicators_latest": ind_latest, "error": None}

    except Exception as e:
        tb = traceback.format_exc()
        LOG.exception('prediction error: %s', e)
        return {"ticker": ticker, "predictions": [], "error": str(e) + "\n" + tb}


@app.route('/api/predict', methods=['POST'])
def predict_route():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"ticker": None, "predictions": [], "error": "invalid or missing JSON body"}), 400

    ticker = payload.get('ticker')
    days = payload.get('days', 5)
    mode = (payload.get('mode') or 'ml').lower()
    frequency = (payload.get('frequency') or 'daily').lower()
    api_key = payload.get('api_key')
    market_ticker = payload.get('market_ticker')
    manual = None
    # Model params (optional)
    model_type = (payload.get('model') or 'ridge').lower() if isinstance(payload.get('model'), str) else (payload.get('model', {}).get('type', 'ridge') if isinstance(payload.get('model'), dict) else 'ridge')
    window = payload.get('window') if isinstance(payload.get('window'), int) else (payload.get('model', {}).get('window') if isinstance(payload.get('model'), dict) else None)
    ridge_alpha = payload.get('alpha') if isinstance(payload.get('alpha'), (int, float)) else (payload.get('model', {}).get('alpha') if isinstance(payload.get('model'), dict) else 1.0)
    if mode == 'manual':
        manual = {
            'base_price': payload.get('base_price'),
            'drift_pct': payload.get('drift_pct'),
            'vol_pct': payload.get('vol_pct'),
            'slope': payload.get('slope'),
        }

    if not ticker or not isinstance(ticker, str) or ticker.strip() == "":
        return jsonify({"ticker": ticker, "predictions": [], "error": "ticker is required"}), 400

    try:
        days_int = int(days)
    except Exception:
        days_int = 5

    # Attach model params onto Flask global via closure not ideal; pass through in request context via globals
    # Simpler: temporarily set on app config for this call
    app.config['_MODEL_PARAMS'] = {'model_type': model_type, 'window': window, 'ridge_alpha': ridge_alpha, 'api_key': api_key, 'market_ticker': market_ticker}
    result = load_and_predict(ticker, days_int, manual=manual, frequency=frequency)
    app.config.pop('_MODEL_PARAMS', None)
    status = 200 if result.get('error') is None else 500
    return jsonify(result), status


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Stock Prediction API is running"})


@app.route('/debug/history', methods=['GET'])
def debug_history():
    """Debug helper: fetch minimal history and return sanitized request metadata.
    Query params: ticker (required), frequency (daily|weekly|monthly, default=daily)
    """
    ticker = request.args.get('ticker', type=str)
    frequency = (request.args.get('frequency') or 'daily').lower()
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        # allow passing api_key via query string for debugging (not recommended for prod)
        api_key = request.args.get('api_key')
        result = fetch_history(
            ticker.strip().upper(),
            period='120d',
            frequency=frequency,
            outputsize='full',
            return_metadata=True,
            api_key=api_key,
        )
        if isinstance(result, tuple):
            df, meta = result
        else:
            df, meta = result, {}
        info = {
            'provider': meta.get('provider', 'unknown'),
            'request': meta.get('params', {}),  # sanitized (no apikey)
            'url': meta.get('url'),
            'rows': 0 if df is None else int(df.shape[0]),
            'cols': [] if df is None or df.empty else list(df.columns),
        }
        if df is not None and not df.empty:
            idx = df.index
            try:
                info['first'] = idx[0].isoformat()
                info['last'] = idx[-1].isoformat()
            except Exception:
                pass
        return jsonify(info), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/history', methods=['POST'])
def api_history():
    """Return recent history rows for a ticker with sanitized metadata.
    Body: { ticker, frequency, limit?, api_key? }
    """
    payload = request.get_json(force=True, silent=True) or {}
    ticker = (payload.get('ticker') or '').strip()
    # Prefer explicit AV function if provided; else use frequency
    function = (payload.get('function') or '').upper()
    frequency = (payload.get('frequency') or 'daily').lower()
    if function in ('TIME_SERIES_DAILY', 'TIME_SERIES_WEEKLY', 'TIME_SERIES_MONTHLY'):
        frequency = {
            'TIME_SERIES_DAILY': 'daily',
            'TIME_SERIES_WEEKLY': 'weekly',
            'TIME_SERIES_MONTHLY': 'monthly',
        }[function]
    limit = payload.get('limit') or 100
    api_key = payload.get('api_key')
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        result = fetch_history(
            ticker.upper(),
            period='120d',
            frequency=frequency,
            outputsize='full',
            return_metadata=True,
            api_key=api_key,
        )
        if isinstance(result, tuple):
            df, meta = result
        else:
            df, meta = result, {}
        rows = []
        if df is not None and not df.empty:
            df2 = df.tail(int(limit))
            for idx, row in df2.iterrows():
                item = {
                    'date': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                }
                for k in ['open','high','low','close','volume']:
                    if k in df2.columns and pd.notna(row.get(k, None)):
                        try:
                            item[k] = float(row[k])
                        except Exception:
                            pass
                rows.append(item)
        return jsonify({
            'provider': meta.get('provider', 'alphavantage'),
            'request': meta.get('params', {}),
            'url': meta.get('url'),
            'rows': rows,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/quote', methods=['POST'])
def api_quote():
    """Return current GLOBAL_QUOTE from Alpha Vantage for a ticker.
    Body: { ticker }
    """
    payload = request.get_json(force=True, silent=True) or {}
    ticker = (payload.get('ticker') or '').strip()
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        data = fetch_global_quote_av(ticker)
        if not isinstance(data, dict):
            return jsonify({"error": "unexpected response"}), 500
        return jsonify(data), 200 if 'error' not in data else 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/indicators', methods=['POST'])
def api_indicators():
    """Compute and return technical indicators for a ticker based on AV history.
    Body: { ticker, function?, frequency?, limit? }
    """
    payload = request.get_json(force=True, silent=True) or {}
    ticker = (payload.get('ticker') or '').strip()
    function = (payload.get('function') or '').upper()
    frequency = (payload.get('frequency') or 'daily').lower()
    limit = payload.get('limit') or 120
    if function in ('TIME_SERIES_DAILY', 'TIME_SERIES_WEEKLY', 'TIME_SERIES_MONTHLY'):
        frequency = {
            'TIME_SERIES_DAILY': 'daily',
            'TIME_SERIES_WEEKLY': 'weekly',
            'TIME_SERIES_MONTHLY': 'monthly',
        }[function]
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        result = fetch_history(
            ticker.upper(),
            period='120d',
            frequency=frequency,
            outputsize='full',
            return_metadata=True,
        )
        if isinstance(result, tuple):
            df, meta = result
        else:
            df, meta = result, {}
        if df is None or df.empty:
            return jsonify({"error": "no history available from provider"}), 500
        ind = compute_technical_indicators(df)
        ind2 = ind.tail(int(limit))
        rows = []
        for idx, row in ind2.iterrows():
            def _safe(name):
                try:
                    val = row[name]
                    return None if pd.isna(val) else float(val)
                except Exception:
                    return None
            item = {
                'date': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'close': _safe('close') if 'close' in ind2.columns else None,
                'sma_5': _safe('sma_5'),
                'sma_10': _safe('sma_10'),
                'sma_20': _safe('sma_20'),
                'ema_12': _safe('ema_12'),
                'ema_20': _safe('ema_20'),
                'ema_26': _safe('ema_26'),
                'rsi_14': _safe('rsi_14'),
                'macd': _safe('macd'),
                'macd_signal': _safe('macd_signal'),
                'macd_hist': _safe('macd_hist'),
                'bb_mid': _safe('bb_mid'),
                'bb_upper': _safe('bb_upper'),
                'bb_lower': _safe('bb_lower'),
                'bb_width': _safe('bb_width'),
                'atr_14': _safe('atr_14'),
                'obv': _safe('obv') if 'obv' in ind2.columns else None,
            }
            rows.append(item)
        return jsonify({
            'provider': meta.get('provider', 'alphavantage'),
            'request': meta.get('params', {}),
            'url': meta.get('url'),
            'rows': rows,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/features-columns', methods=['POST'])
def api_features_columns():
    """Return the final feature columns used for model training given the current request.
    Body: { ticker, frequency?, window?, market_ticker? }
    """
    payload = request.get_json(force=True, silent=True) or {}
    ticker = (payload.get('ticker') or '').strip()
    frequency = (payload.get('frequency') or 'daily').lower()
    window = payload.get('window')
    market_ticker = payload.get('market_ticker')
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        # Fetch asset history
        result = fetch_history(
            ticker.upper(),
            period='120d',
            frequency=frequency,
            outputsize='full',
            return_metadata=False,
        )
        df = result if not isinstance(result, tuple) else result[0]
        if df is None or df.empty:
            return jsonify({"error": "no history available from provider"}), 500

        fundamentals = {}
        # Optional market correlation
        if market_ticker:
            try:
                m_hist = fetch_history(market_ticker.strip().upper(), period='120d', frequency=frequency, outputsize='full')
                if m_hist is not None and not m_hist.empty and 'close' in m_hist.columns:
                    fundamentals['market_close'] = m_hist['close'].astype(float)
            except Exception:
                pass

        # Build features and simulate training slice
        try:
            from .features import assemble_features
        except Exception:
            import features  # type: ignore
            assemble_features = features.assemble_features  # type: ignore[attr-defined]

        feats = assemble_features(df, fundamentals)
        if isinstance(window, int) and window > 0 and len(feats) > window:
            feats = feats.iloc[-window:].copy()
        # Add target for inspection then drop
        feats['target'] = feats['close'].shift(-1)
        feats = feats.dropna().copy()
        cols = [c for c in feats.columns if c != 'target']
        return jsonify({"columns": cols, "count": len(cols)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)