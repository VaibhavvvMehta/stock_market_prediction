import os
import logging
from datetime import datetime
import requests
import pandas as pd
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # 1) Load from current working directory if present
    load_dotenv()
    # 2) Also try the backend folder explicitly so running from repo root still loads backend/.env
    backend_env = Path(__file__).with_name('.env')
    if backend_env.exists():
        load_dotenv(backend_env, override=False)
except Exception:
    pass

LOG = logging.getLogger(__name__)


def get_provider():
    """Return configured data provider. Default: 'alphavantage'."""
    return os.environ.get('DATA_PROVIDER', 'alphavantage').lower()


def fetch_history(
    ticker: str,
    period: str = "120d",
    frequency: str = "daily",
    outputsize: str = "compact",
    return_metadata: bool = False,
    api_key: Optional[str] = None,
):
    """
    Fetch historical price data for ticker.
    Returns a DataFrame indexed by datetime with at least 'close' column and (when available) 'open','high','low','volume'.
    frequency: 'daily' | 'weekly' | 'monthly'
    """
    provider = get_provider()
    frequency = (frequency or 'daily').lower()

    if provider == 'yfinance':
        try:
            import yfinance as yf

            # For yfinance, accept .NS/.BSE; default to .NS if no suffix
            t = ticker.strip().upper()
            if not (t.endswith('.NS') or t.endswith('.BSE')):
                t = t + '.NS'
            yf_t = yf.Ticker(t)
            if frequency == 'weekly':
                df = yf_t.history(period=period, interval='1wk')
            elif frequency == 'monthly':
                df = yf_t.history(period=period, interval='1mo')
            else:
                df = yf_t.history(period=period)
            if df is None:
                return pd.DataFrame()
            df = df.rename(columns={c: c.lower() for c in df.columns})
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass
            return df
        except Exception as e:
            LOG.exception('yfinance fetch failed: %s', e)
            raise

    if provider == 'alphavantage':
        key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY')
        if not key:
            raise RuntimeError('ALPHA_VANTAGE_API_KEY is not set')

        symbol = ticker.strip().upper()
        url = 'https://www.alphavantage.co/query'
        # Use non-adjusted endpoints only (no adjusted endpoints)
        fn_map = {
            'daily': 'TIME_SERIES_DAILY',
            'weekly': 'TIME_SERIES_WEEKLY',
            'monthly': 'TIME_SERIES_MONTHLY',
        }
        fn = fn_map.get(frequency, 'TIME_SERIES_DAILY')
        # Build params; only include outputsize for daily (ignored for weekly/monthly)
        params = {
            'function': fn,
            'symbol': symbol,
            'apikey': key,
        }
        if frequency == 'daily':
            _out = outputsize if outputsize else 'full'
            params['outputsize'] = _out

        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
        # Match non-adjusted keys only
        ts = (
            j.get('Time Series (Daily)')
            or j.get('Weekly Time Series')
            or j.get('Monthly Time Series')
        )
        if not ts:
            LOG.error('AlphaVantage unexpected response: %s', j)
            return (pd.DataFrame(), {'provider': 'alphavantage', 'url': url, 'params': {k: v for k, v in params.items() if k != 'apikey'}, 'raw_keys': list(j.keys())}) if return_metadata else pd.DataFrame()

        records = []
        for date_str, vals in ts.items():
            try:
                date = datetime.fromisoformat(date_str)
            except Exception:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            # non-adjusted close/volume keys
            close = vals.get('4. close') or vals.get('close')
            open_ = vals.get('1. open') or vals.get('open')
            high = vals.get('2. high') or vals.get('high')
            low = vals.get('3. low') or vals.get('low')
            volume = vals.get('5. volume') or vals.get('volume')
            if close is None:
                continue
            row = {'date': date, 'close': float(close)}
            if open_ is not None:
                row['open'] = float(open_)
            if high is not None:
                row['high'] = float(high)
            if low is not None:
                row['low'] = float(low)
            if volume is not None:
                try:
                    row['volume'] = float(volume)
                except Exception:
                    pass
            records.append(row)

        df = pd.DataFrame(records)
        if df.empty:
            return (df, {'provider': 'alphavantage', 'url': url, 'params': {k: v for k, v in params.items() if k != 'apikey'}}) if return_metadata else df
        df = df.sort_values('date')
        df = df.set_index('date')
        return (df, {'provider': 'alphavantage', 'url': url, 'params': {k: v for k, v in params.items() if k != 'apikey'}}) if return_metadata else df

    raise RuntimeError(f'Unsupported DATA_PROVIDER: {provider}')


def fetch_fundamentals_av(ticker: str, api_key: Optional[str] = None) -> dict:
    """Fetch Alpha Vantage OVERVIEW fundamentals (EPS, PE, PEG, PB)."""
    key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not key:
        return {}
    symbol = ticker.strip().upper()
    url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'OVERVIEW',
        'symbol': symbol,
        'apikey': key,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        LOG.exception('AlphaVantage OVERVIEW failed: %s', e)
        return {}
    out = {}
    for k_in, k_out in [
        ('EPS', 'eps'),
        ('PERatio', 'pe'),
        ('PEGRatio', 'peg'),
        ('PriceToBookRatio', 'pb'),
    ]:
        v = j.get(k_in)
        try:
            out[k_out] = float(v) if v not in (None, 'None', '') else None
        except Exception:
            out[k_out] = None
    return out


def fetch_global_quote_av(ticker: str, api_key: Optional[str] = None) -> dict:
    """Fetch Alpha Vantage GLOBAL_QUOTE for the given symbol and normalize fields."""
    key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not key:
        return {"error": "ALPHA_VANTAGE_API_KEY is not set"}
    symbol = ticker.strip().upper()
    url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': key,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        LOG.exception('AlphaVantage GLOBAL_QUOTE failed: %s', e)
        return {"error": str(e)}

    gq = j.get('Global Quote') or j.get('GlobalQuote') or {}
    if not gq:
        # Return raw keys for debugging
        return {
            "error": "No Global Quote returned",
            "raw_keys": list(j.keys()),
            "url": url,
            "request": {k: v for k, v in params.items() if k != 'apikey'},
        }

    def _f(k):
        v = gq.get(k)
        if v in (None, 'None', ''):
            return None
        try:
            return float(v)
        except Exception:
            return v

    out = {
        'symbol': gq.get('01. symbol') or symbol,
        'open': _f('02. open'),
        'high': _f('03. high'),
        'low': _f('04. low'),
        'price': _f('05. price'),
        'volume': _f('06. volume'),
        'latest_trading_day': gq.get('07. latest trading day'),
        'previous_close': _f('08. previous close'),
        'change': _f('09. change'),
        'change_percent': gq.get('10. change percent'),
        'url': url,
        'request': {k: v for k, v in params.items() if k != 'apikey'},
        'provider': 'alphavantage',
    }
    return out
