from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from typing import List, Dict, Literal

try:
    from .features import assemble_features
except Exception:
    try:
        import features  # type: ignore
        assemble_features = features.assemble_features  # type: ignore[attr-defined]
    except Exception as e:
        raise


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = {c.lower(): c for c in out.columns}
    # Normalize column names to lowercase
    out.columns = [c.lower() for c in out.columns]
    # Fill missing ohlc with close as a fallback for iterative predictions
    for col in ['open', 'high', 'low']:
        if col not in out.columns and 'close' in out.columns:
            out[col] = out['close']
    if 'volume' not in out.columns:
        out['volume'] = 0.0
    return out


def train_and_predict_ml(
    df: pd.DataFrame,
    fundamentals: Dict | None,
    steps: int = 5,
    *,
    model_type: Literal['ridge', 'rf'] = 'ridge',
    window: int | None = None,
    ridge_alpha: float = 1.0,
) -> List[float]:
    """
    Train a lightweight ML model on historical features to predict next-step close.
    Iteratively predict multiple future steps by appending predictions and recomputing features.
    Returns list of predicted close prices (floats) of length `steps`.
    """
    if df is None or df.empty:
        raise ValueError("empty history")

    hist = _ensure_ohlcv(df)
    if window is not None and window > 0 and len(hist) > window:
        hist = hist.iloc[-window:].copy()

    # Build features and target (next close)
    feats = assemble_features(hist, fundamentals)
    if 'close' not in feats.columns:
        # ensure close is available as target
        raise ValueError("history missing 'close' column after feature assembly")

    feats['target'] = feats['close'].shift(-1)
    feats_model = feats.dropna().copy()
    if len(feats_model) < 60:
        # need enough history to be meaningful
        raise ValueError("insufficient data for ML (need >= 60 rows after features)")

    y = feats_model['target']
    X = feats_model.drop(columns=['target'])

    # Simple regularized linear model
    if model_type == 'rf':
        model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    else:
        model = Ridge(alpha=float(ridge_alpha), random_state=42)
    model.fit(X, y)

    # Iterative multi-step forecasting
    preds: List[float] = []
    sim = hist.copy()
    for _ in range(steps):
        feats_sim = assemble_features(sim, fundamentals).dropna().copy()
        X_last = feats_sim.iloc[[-1]].copy()
        # Remove any accidental target if present
        if 'target' in X_last.columns:
            X_last = X_last.drop(columns=['target'])
        next_close = float(model.predict(X_last)[0])
        preds.append(next_close)

        # Append new row assuming close=open=high=low=pred; volume carry-forward
        last_idx = sim.index[-1]
        next_idx = last_idx + (sim.index[-1] - sim.index[-2] if len(sim) > 1 else pd.Timedelta(days=1))
        new_row = {
            'open': next_close,
            'high': next_close,
            'low': next_close,
            'close': next_close,
            'volume': float(sim['volume'].iloc[-1]) if 'volume' in sim.columns else 0.0,
        }
        sim = pd.concat([sim, pd.DataFrame([new_row], index=[next_idx])])

    return preds
