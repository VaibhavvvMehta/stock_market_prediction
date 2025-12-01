import sys
sys.path.append('backend')
from features import compute_technical_indicators
import pandas as pd
import numpy as np

# Expected comprehensive feature set
expected_features = [
    # Trend indicators
    'sma_5', 'sma_10', 'sma_20', 'sma_50',
    'ema_12', 'ema_20', 'ema_26', 'ema_50',
    # Momentum indicators  
    'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'stoch_k_14', 'stoch_d_3',
    # Volatility indicators
    'tr', 'atr_14', 'bb_mid', 'bb_upper', 'bb_lower', 'bb_width',
    # Volume indicators
    'obv', 'mfi_14', 'vol_sma_20', 'volume_spike',
    # Price action
    'hl_pct', 'co_pct', 'cp_pct', 'ret_1', 'ret_5',
    # Lags
    'close_lag_1', 'close_lag_3', 'close_lag_5', 'close_lag_10',
    # Rolling stats
    'rolling_std_10', 'rolling_std_20', 'rolling_skew_10', 'rolling_kurt_10', 'rolling_zscore_10',
    # ADX & DI
    'adx_14', 'plus_di_14', 'minus_di_14',
    # Patterns
    'doji', 'bull_engulf', 'bear_engulf', 'support_20', 'resistance_20', 'breakout', 'breakdown',
    # Correlation & regime
    'corr_with_index_20', 'regime_trend'
]

# Generate sample data
np.random.seed(42)
n = 120
base = np.random.normal(100, 2, n).cumsum() + 1500
df = pd.DataFrame({
    'Open': base + np.random.normal(0, 1, n),
    'High': base + np.random.uniform(0, 5, n),
    'Low': base - np.random.uniform(0, 5, n),
    'Close': base + np.random.normal(0, 1, n),
    'Volume': np.random.randint(100000, 500000, n),
    'market_index': np.random.normal(50, 1, n).cumsum() + 4000
}, index=pd.date_range('2024-01-01', periods=n))

print("Input columns:", list(df.columns))
result = compute_technical_indicators(df)
calculated_features = set(result.columns)

print(f'\nTotal calculated columns: {len(calculated_features)}')

# Check for missing features
missing = [f for f in expected_features if f not in calculated_features]
if missing:
    print(f'\nMISSING FEATURES ({len(missing)}):')
    for f in missing:
        print(f'  - {f}')
else:
    print('\nAll expected features are present!')

# Check for extra features not in expected list
extra = [f for f in calculated_features if f not in expected_features and f not in ['open', 'high', 'low', 'close', 'volume', 'market_index']]
if extra:
    print(f'\nEXTRA FEATURES ({len(extra)}):')
    for f in extra:
        print(f'  + {f}')

print(f'\nExpected: {len(expected_features)}')
print(f'Calculated: {len(calculated_features)}')

# Show sample values for key indicators
print(f'\nSample values for last row (key indicators):')
last_row = result.iloc[-1]
key_indicators = ['close', 'sma_20', 'ema_20', 'rsi_14', 'macd', 'atr_14', 'volume_spike', 'corr_with_index_20']
for col in key_indicators:
    if col in result.columns:
        val = last_row[col]
        if pd.notna(val):
            print(f'{col}: {val:.4f}')
        else:
            print(f'{col}: NaN')
    else:
        print(f'{col}: NOT FOUND')