import sys
sys.path.append('backend')
from features import compute_technical_indicators
import pandas as pd
import numpy as np

# Generate sample OHLCV data for testing
np.random.seed(42)
n = 120
dates = pd.date_range('2024-01-01', periods=n)
base_price = 150
price_walk = np.random.normal(0, 2, n).cumsum()
prices = base_price + price_walk

df = pd.DataFrame({
    'Open': prices + np.random.normal(0, 0.5, n),
    'High': prices + np.random.uniform(0, 2, n),
    'Low': prices - np.random.uniform(0, 2, n),
    'Close': prices + np.random.normal(0, 0.3, n),
    'Volume': np.random.randint(100000, 500000, n),
    'market_index': 4000 + np.random.normal(0, 50, n).cumsum()
}, index=dates)

print("=== FEATURE AUDIT ===")
print(f"Input data shape: {df.shape}")
print(f"Input columns: {list(df.columns)}")

# Compute features
result = compute_technical_indicators(df)
computed_features = sorted(result.columns)

print(f"\nComputed features ({len(computed_features)}):")
for i, feature in enumerate(computed_features, 1):
    print(f"{i:2d}. {feature}")

# Check for key missing features based on original spec
expected_missing = []

# Check for each category
print("\n=== CATEGORY ANALYSIS ===")

# 1. Trend indicators (should have 8)
trend_features = [f for f in computed_features if any(x in f for x in ['sma', 'ema', 'macd'])]
print(f"Trend features ({len(trend_features)}): {trend_features}")

# 2. Momentum indicators (should have 10+)
momentum_features = [f for f in computed_features if any(x in f for x in ['rsi', 'stoch', 'adx', 'di'])]
print(f"Momentum features ({len(momentum_features)}): {momentum_features}")

# 3. Volatility indicators (should have 11+)
volatility_features = [f for f in computed_features if any(x in f for x in ['bb', 'atr', 'tr', 'std'])]
print(f"Volatility features ({len(volatility_features)}): {volatility_features}")

# 4. Volume indicators (should have 6+)
volume_features = [f for f in computed_features if any(x in f for x in ['vol', 'obv', 'mfi', 'spike'])]
print(f"Volume features ({len(volume_features)}): {volume_features}")

# 5. Price action indicators (should have 21+)
price_action = [f for f in computed_features if any(x in f for x in ['ret', 'pct', 'lag', 'support', 'resistance', 'breakout', 'breakdown'])]
print(f"Price action features ({len(price_action)}): {price_action}")

# 6. Pattern indicators
pattern_features = [f for f in computed_features if any(x in f for x in ['doji', 'engulf'])]
print(f"Pattern features ({len(pattern_features)}): {pattern_features}")

# 7. Rolling statistics
rolling_features = [f for f in computed_features if any(x in f for x in ['rolling', 'zscore'])]
print(f"Rolling stats features ({len(rolling_features)}): {rolling_features}")

# 8. Correlation & regime
corr_regime = [f for f in computed_features if any(x in f for x in ['corr', 'regime'])]
print(f"Correlation/Regime features ({len(corr_regime)}): {corr_regime}")

# Check for specific missing features from the original request
original_spec_features = [
    # Trend (8 total)
    'sma_5', 'sma_10', 'sma_20', 'sma_50',
    'ema_12', 'ema_20', 'ema_26', 'ema_50',
    
    # Momentum (10+ total)
    'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'stoch_k_14', 'stoch_d_3',
    'adx_14', 'plus_di_14', 'minus_di_14',
    
    # Volatility (11+ total)  
    'tr', 'atr_14', 'bb_mid', 'bb_upper', 'bb_lower', 'bb_width',
    'rolling_std_10', 'rolling_std_20',
    
    # Volume (6+ total)
    'obv', 'mfi_14', 'vol_sma_20', 'volume_spike',
    
    # Price action (21+ total)
    'hl_pct', 'co_pct', 'cp_pct', 
    'ret_1', 'ret_5',
    'close_lag_1', 'close_lag_3', 'close_lag_5', 'close_lag_10',
    'support_20', 'resistance_20', 'breakout', 'breakdown',
    
    # Rolling statistics
    'rolling_skew_10', 'rolling_kurt_10', 'rolling_zscore_10',
    
    # Patterns
    'doji', 'bull_engulf', 'bear_engulf',
    
    # Correlation & regime
    'corr_with_index_20', 'regime_trend'
]

print(f"\n=== MISSING FEATURES CHECK ===")
missing_from_spec = []
for feature in original_spec_features:
    if feature not in computed_features:
        missing_from_spec.append(feature)

if missing_from_spec:
    print(f"Missing from original spec ({len(missing_from_spec)}):")
    for feature in missing_from_spec:
        print(f"  - {feature}")
else:
    print("✓ All features from original spec are present!")

# Show some sample values
print(f"\n=== SAMPLE VALUES (last row) ===")
last_row = result.iloc[-1]
sample_features = ['close', 'sma_20', 'ema_20', 'rsi_14', 'macd', 'atr_14', 'volume_spike', 'corr_with_index_20']
for feature in sample_features:
    if feature in result.columns:
        val = last_row[feature]
        print(f"{feature}: {val:.4f}" if pd.notna(val) else f"{feature}: NaN")

print(f"\nTotal features computed: {len(computed_features)}")
print(f"Expected from spec: {len(original_spec_features)}")