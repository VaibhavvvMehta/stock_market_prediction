import sys
sys.path.append('backend')
from features import assemble_features
import pandas as pd
import numpy as np

print("=== TESTING ASSEMBLE_FEATURES OUTPUT ===")

# Generate synthetic OHLCV data
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
}, index=dates)

print(f"Input data shape: {df.shape}")
print(f"Input columns: {list(df.columns)}")

# Test with market index
fundamentals = {
    'market_index': pd.Series(4000 + np.random.normal(0, 50, n).cumsum(), index=dates)
}

# Call assemble_features (this is what the API endpoint calls)
result = assemble_features(df, include_fundamentals=True, fundamentals=fundamentals)

print(f"\nAfter assemble_features:")
print(f"Output shape: {result.shape}")
print(f"Total features: {len(result.columns)}")

# List all features
print(f"\nAll features ({len(result.columns)}):")
for i, col in enumerate(sorted(result.columns), 1):
    print(f"{i:2d}. {col}")

# Check for key indicators that user might be expecting
key_indicators = [
    'sma_5', 'sma_10', 'sma_20', 'sma_50',
    'ema_12', 'ema_20', 'ema_26', 'ema_50', 
    'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'stoch_k_14', 'stoch_d_3',
    'bb_upper', 'bb_lower', 'bb_mid', 'bb_width',
    'atr_14', 'tr',
    'adx_14', 'plus_di_14', 'minus_di_14',
    'obv', 'mfi_14', 'volume_spike',
    'corr_with_index_20', 'regime_trend'
]

print(f"\n=== KEY INDICATORS CHECK ===")
missing_indicators = []
present_indicators = []

for indicator in key_indicators:
    if indicator in result.columns:
        present_indicators.append(indicator)
        print(f"✓ {indicator}")
    else:
        missing_indicators.append(indicator)
        print(f"✗ {indicator}")

print(f"\nSUMMARY:")
print(f"Present: {len(present_indicators)}/{len(key_indicators)}")
print(f"Missing: {len(missing_indicators)}")

if missing_indicators:
    print(f"\nMissing indicators: {missing_indicators}")
else:
    print(f"\n🎉 All key indicators are present!")

# Show some sample values
print(f"\n=== SAMPLE VALUES (last row) ===")
last_row = result.iloc[-1]
sample_cols = ['close', 'sma_20', 'ema_20', 'rsi_14', 'macd', 'atr_14', 'volume_spike', 'corr_with_index_20']
for col in sample_cols:
    if col in result.columns:
        val = last_row[col]
        print(f"{col}: {val:.4f}" if pd.notna(val) else f"{col}: NaN")

print(f"\nNaN count per feature:")
nan_counts = result.isna().sum()
features_with_nans = nan_counts[nan_counts > 0].sort_values(ascending=False)
if len(features_with_nans) > 0:
    print("Features with NaN values:")
    for feature, count in features_with_nans.head(10).items():
        print(f"  {feature}: {count} NaN values")
else:
    print("No NaN values found in any features!")