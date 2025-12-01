import pandas as pd
import numpy as np
from typing import Optional
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute full feature set from raw OHLCV data (spec)."""
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    close = pd.to_numeric(out.get('close'), errors='coerce')
    open_ = pd.to_numeric(out.get('open', close), errors='coerce')
    high = pd.to_numeric(out.get('high', close), errors='coerce')
    low = pd.to_numeric(out.get('low', close), errors='coerce')
    volume = pd.to_numeric(out.get('volume', pd.Series(0, index=out.index)), errors='coerce')
    prev_close = close.shift(1)

    # Trend MAs
    for w, name in [(5,'sma_5'),(10,'sma_10'),(20,'sma_20'),(50,'sma_50')]:
        out[name] = close.rolling(w, min_periods=w).mean()
    for w, name in [(12,'ema_12'),(20,'ema_20'),(26,'ema_26'),(50,'ema_50')]:
        out[name] = close.ewm(span=w, adjust=False, min_periods=w).mean()

    # MACD
    out['macd'] = out['ema_12'] - out['ema_26']
    out['macd_signal'] = out['macd'].ewm(span=9, adjust=False).mean()
    out['macd_hist'] = out['macd'] - out['macd_signal']

    # RSI
    out['rsi_14'] = RSIIndicator(close, window=14, fillna=False).rsi()

    # Bollinger Bands
    bb_mid = out['sma_20']
    std20 = close.rolling(20, min_periods=20).std(ddof=0)
    out['bb_mid'] = bb_mid
    out['bb_upper'] = bb_mid + 2 * std20
    out['bb_lower'] = bb_mid - 2 * std20
    out['bb_width'] = (out['bb_upper'] - out['bb_lower']) / bb_mid.replace(0, np.nan)

    # Stochastic
    lowest_low_14 = low.rolling(14, min_periods=14).min()
    highest_high_14 = high.rolling(14, min_periods=14).max()
    stoch_k = (close - lowest_low_14) / (highest_high_14 - lowest_low_14).replace(0, np.nan) * 100.0
    out['stoch_k_14'] = stoch_k
    out['stoch_d_3'] = stoch_k.rolling(3, min_periods=3).mean()
    out['stoch_k'] = out['stoch_k_14']
    out['stoch_d'] = out['stoch_d_3']

    # ADX & DI
    try:
        adx_ind = ADXIndicator(high=high, low=low, close=close, window=14, fillna=False)
        out['adx_14'] = adx_ind.adx()
        out['plus_di_14'] = adx_ind.adx_pos()
        out['minus_di_14'] = adx_ind.adx_neg()
    except Exception:
        out['adx_14'] = np.nan
        out['plus_di_14'] = np.nan
        out['minus_di_14'] = np.nan
    out['di_pos_14'] = out['plus_di_14']
    out['di_neg_14'] = out['minus_di_14']

    # True Range & ATR
    tr_components = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1)
    out['tr'] = tr_components.max(axis=1)
    out['atr_14'] = out['tr'].ewm(span=14, adjust=False, min_periods=14).mean()

    # Volume features
    if 'volume' in out.columns:
        out['vol_sma_20'] = volume.rolling(20, min_periods=20).mean()
        with np.errstate(divide='ignore', invalid='ignore'):
            out['volume_spike'] = volume / out['vol_sma_20']
        out['vol_spike'] = out['volume_spike']
        direction = np.sign(close - prev_close).replace(0, 0)
        out['obv'] = (direction * volume).cumsum()
        tp = (high + low + close) / 3.0
        mf = tp * volume
        tp_prev = tp.shift(1)
        pos_flow = mf.where(tp > tp_prev, 0.0)
        neg_flow = mf.where(tp < tp_prev, 0.0)
        pos_sum = pos_flow.rolling(14, min_periods=14).sum()
        neg_sum = neg_flow.rolling(14, min_periods=14).sum()
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = pos_sum / neg_sum
            out['mfi_14'] = 100 - (100 / (1 + ratio))
    else:
        out['vol_sma_20'] = np.nan
        out['volume_spike'] = np.nan
        out['vol_spike'] = np.nan
        out['obv'] = np.nan
        out['mfi_14'] = np.nan

    # Support / Resistance & breakouts
    out['support_20'] = close.rolling(20, min_periods=1).min()
    out['resistance_20'] = close.rolling(20, min_periods=1).max()
    out['breakout'] = (close > out['resistance_20'].shift(1)).astype(int)
    out['breakdown'] = (close < out['support_20'].shift(1)).astype(int)

    # Lags & returns
    out['close_lag_1'] = close.shift(1)
    out['close_lag_3'] = close.shift(3)
    out['close_lag_5'] = close.shift(5)
    out['close_lag_10'] = close.shift(10)
    out['ret_1'] = close / out['close_lag_1'] - 1.0
    out['ret_5'] = close / out['close_lag_5'] - 1.0
    out['lag_1'] = out['close_lag_1']
    out['lag_3'] = out['close_lag_3']
    out['lag_5'] = out['close_lag_5']
    out['lag_10'] = out['close_lag_10']

    # Price action
    with np.errstate(divide='ignore', invalid='ignore'):
        out['hl_pct'] = (high - low) / open_ * 100.0
        out['co_pct'] = (close - open_) / open_ * 100.0
        out['cp_pct'] = (close - prev_close) / prev_close * 100.0

    # Rolling stats
    out['rolling_std_10'] = close.rolling(10, min_periods=5).std(ddof=0)
    out['rolling_std_20'] = close.rolling(20, min_periods=10).std(ddof=0)
    out['rolling_skew_10'] = close.rolling(10, min_periods=10).skew()
    out['rolling_kurt_10'] = close.rolling(10, min_periods=10).kurt()
    mu10 = close.rolling(10, min_periods=10).mean()
    std10 = out['rolling_std_10']
    out['rolling_zscore_10'] = (close - mu10) / std10.replace(0, np.nan)

    # Candle patterns
    if all(k in out.columns for k in ['open','close','high','low']):
        body = (out['close'] - out['open']).abs()
        rng = (out['high'] - out['low']).replace(0, np.nan)
        out['doji'] = (body / rng < 0.1).astype(int)
        prev_open = out['open'].shift(1)
        prev_cls = out['close'].shift(1)
        prev_body_low = np.minimum(prev_open, prev_cls)
        prev_body_high = np.maximum(prev_open, prev_cls)
        curr_body_low = np.minimum(out['open'], out['close'])
        curr_body_high = np.maximum(out['open'], out['close'])
        out['bull_engulf'] = ((out['close'] > out['open']) & (curr_body_low <= prev_body_low) & (curr_body_high >= prev_body_high)).astype(int)
        out['bear_engulf'] = ((out['close'] < out['open']) & (curr_body_low <= prev_body_low) & (curr_body_high >= prev_body_high)).astype(int)
    else:
        out['doji'] = 0
        out['bull_engulf'] = 0
        out['bear_engulf'] = 0

    # Correlation with market index if present
    if 'market_index' in out.columns:
        idx_vals = pd.to_numeric(out['market_index'], errors='coerce')
        r_asset = close.pct_change(1)
        r_index = idx_vals.pct_change(1)
        out['corr_with_index_20'] = r_asset.rolling(20, min_periods=10).corr(r_index)
    else:
        out['corr_with_index_20'] = np.nan

    # Regime
    out['regime_trend'] = (out['adx_14'] >= 25).astype(int)

    return out


def assemble_features(df: pd.DataFrame, include_fundamentals: bool = False, fundamentals: Optional[dict] = None) -> pd.DataFrame:
    """Return feature matrix.

    include_fundamentals: if True and fundamentals dict provided, append f_eps,f_pe,f_peg,f_pb.
    fundamentals: optional dict. For backward compatibility, if a dict is passed as second argument
                  (older signature assemble_features(df, fundamentals)), treat it as fundamentals.
    """
    # Backwards compatibility: if include_fundamentals is actually a dict
    if isinstance(include_fundamentals, dict) and fundamentals is None:
        fundamentals = include_fundamentals
        include_fundamentals = True
    feats = compute_technical_indicators(df)
    if include_fundamentals and fundamentals:
        for k in ['eps', 'pe', 'peg', 'pb']:
            val = fundamentals.get(k)
            feats[f'f_{k}'] = float(val) if val is not None else np.nan
    # Optional market index passed inside fundamentals as 'market_index' Series
    if fundamentals and isinstance(fundamentals.get('market_index'), pd.Series):
        feats['market_index'] = fundamentals['market_index'].reindex(feats.index).astype(float)
    
    # Drop rows with insufficient data, but be less aggressive about NaNs
    # Only require basic OHLCV data and some key indicators to be present
    required_cols = ['open', 'high', 'low', 'close']
    available_required = [col for col in required_cols if col in feats.columns]
    
    if available_required:
        # Drop rows where basic OHLCV data is missing
        feats = feats.dropna(subset=available_required).copy()
        
        # Also drop rows where too many features are NaN (more than 80% NaN)
        # This keeps rows with some NaN values (normal for indicators) but drops truly problematic rows
        max_nan_threshold = len(feats.columns) * 0.8
        feats = feats.loc[feats.isna().sum(axis=1) <= max_nan_threshold].copy()
    else:
        # Fallback: just remove rows where ALL values are NaN
        feats = feats.dropna(how='all').copy()
    
    return feats