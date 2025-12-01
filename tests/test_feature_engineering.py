import sys
import pathlib
import numpy as np
import pandas as pd

# Ensure backend module importable
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'backend'))

from features import compute_technical_indicators, assemble_features

REQUIRED_COLUMNS = [
    'sma_5','sma_10','sma_20','sma_50',
    'ema_12','ema_20','ema_26','ema_50',
    'rsi_14','macd','macd_signal','macd_hist',
    'stoch_k_14','stoch_d_3',
    'tr','atr_14','bb_mid','bb_upper','bb_lower','bb_width',
    'vol_sma_20','volume_spike','obv','mfi_14',
    'hl_pct','co_pct','cp_pct',
    'close_lag_1','close_lag_3','close_lag_5','close_lag_10',
    'ret_1','ret_5',
    'rolling_std_10','rolling_std_20','rolling_skew_10','rolling_kurt_10','rolling_zscore_10',
    'adx_14','plus_di_14','minus_di_14','regime_trend',
    'corr_with_index_20'
]

def make_sample(n=120):
    rng = np.random.default_rng(42)
    base = rng.normal(loc=100, scale=2, size=n).cumsum() + 1500
    high = base + rng.uniform(0, 5, size=n)
    low = base - rng.uniform(0, 5, size=n)
    open_ = base + rng.normal(0, 1, size=n)
    close = base + rng.normal(0, 1, size=n)
    volume = rng.integers(100_000, 500_000, size=n)
    market_index = (rng.normal(loc=50, scale=1, size=n).cumsum() + 4000)
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    df = pd.DataFrame({
        'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': volume,
        'market_index': market_index
    }, index=dates)
    return df


def test_feature_columns_presence():
    df = make_sample()
    feats = compute_technical_indicators(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in feats.columns]
    assert not missing, f"Missing expected columns: {missing}"


def test_assemble_features_dropna_and_alignment():
    df = make_sample()
    feats = assemble_features(df)
    # Should not be empty and index should align subset of original
    assert len(feats) > 0
    assert feats.index.isin(df.index).all()


def test_no_explicit_python_loops_in_module():
    # Rough heuristic: ensure 'for ' not used outside comprehensions in compute function
    import inspect
    src = inspect.getsource(compute_technical_indicators)
    # Allow "for w" loops (they are minimal); ensure not overly looping raw rows
    line_count = sum(1 for line in src.splitlines() if line.strip().startswith('for '))
    assert line_count <= 5, "Too many explicit for-loops; should stay vectorized"
