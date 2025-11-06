import pandas as pd
import numpy as np
from typing import Optional
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute a set of technical indicators on OHLCV DataFrame.
    Expects columns: close, open, high, low, volume (some may be missing; we guard).
    Returns a new DataFrame with added indicator columns.
    """
    out = df.copy()
    close = out['close'] if 'close' in out.columns else out.iloc[:, 0]

    # Moving averages
    out['sma_5'] = SMAIndicator(close, window=5, fillna=False).sma_indicator()
    out['sma_10'] = SMAIndicator(close, window=10, fillna=False).sma_indicator()
    out['sma_20'] = SMAIndicator(close, window=20, fillna=False).sma_indicator()
    out['ema_12'] = EMAIndicator(close, window=12, fillna=False).ema_indicator()
    out['ema_26'] = EMAIndicator(close, window=26, fillna=False).ema_indicator()
    out['ema_20'] = EMAIndicator(close, window=20, fillna=False).ema_indicator()

    # MACD
    macd = MACD(close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
    out['macd'] = macd.macd()
    out['macd_signal'] = macd.macd_signal()
    out['macd_hist'] = macd.macd_diff()

    # RSI
    out['rsi_14'] = RSIIndicator(close, window=14, fillna=False).rsi()

    # Bollinger Bands mid/upper/lower + width
    bb = BollingerBands(close, window=20, window_dev=2, fillna=False)
    out['bb_mid'] = bb.bollinger_mavg()
    out['bb_upper'] = bb.bollinger_hband()
    out['bb_lower'] = bb.bollinger_lband()
    out['bb_width'] = (out['bb_upper'] - out['bb_lower']) / close

    # ATR (volatility)
    if all(c in out.columns for c in ['high', 'low', 'close']):
        atr = AverageTrueRange(high=out['high'], low=out['low'], close=out['close'], window=14, fillna=False)
        out['atr_14'] = atr.average_true_range()
    else:
        out['atr_14'] = np.nan

    # Volume features
    if 'volume' in out.columns:
        out['vol_sma_20'] = out['volume'].rolling(window=20, min_periods=1).mean()
        out['vol_spike'] = (out['volume'] > (1.5 * out['vol_sma_20'])).astype(int)
        try:
            out['obv'] = OnBalanceVolumeIndicator(close=close, volume=out['volume'], fillna=False).on_balance_volume()
        except Exception:
            out['obv'] = np.nan
    else:
        out['vol_sma_20'] = np.nan
        out['vol_spike'] = 0
        out['obv'] = np.nan

    # Simple support/resistance via rolling extrema
    out['support_20'] = out['close'].rolling(window=20, min_periods=1).min()
    out['resistance_20'] = out['close'].rolling(window=20, min_periods=1).max()
    out['breakout'] = (out['close'] > out['resistance_20'].shift(1)).astype(int)
    out['breakdown'] = (out['close'] < out['support_20'].shift(1)).astype(int)

    # Returns / momentum
    out['ret_1'] = out['close'].pct_change(1)
    out['ret_5'] = out['close'].pct_change(5)

    return out


def assemble_features(df: pd.DataFrame, fundamentals: Optional[dict] = None) -> pd.DataFrame:
    """Add fundamental features (eps, pe, peg, pb) to each row and drop rows with NaNs.
    Returns a clean feature matrix aligned with df.index and includes 'close' for target.
    """
    feats = compute_technical_indicators(df)
    fundamentals = fundamentals or {}
    for k in ['eps', 'pe', 'peg', 'pb']:
        val = fundamentals.get(k)
        feats[f'f_{k}'] = float(val) if val is not None else np.nan

    # Drop rows with insufficient data
    feats = feats.dropna().copy()
    return feats