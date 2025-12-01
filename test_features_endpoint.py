import requests
import json

# Test the features-columns endpoint
url = "http://localhost:5000/api/features-columns"
data = {
    "ticker": "AAPL",
    "frequency": "daily", 
    "window": 60,
    "market_ticker": "SPY"
}

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        columns = result.get('columns', [])
        count = result.get('count', 0)
        
        print(f"\nFeature columns returned ({count}):")
        for i, col in enumerate(sorted(columns), 1):
            print(f"{i:2d}. {col}")
            
        # Check for key missing features
        key_features = ['sma_20', 'ema_20', 'rsi_14', 'macd', 'atr_14', 'volume_spike', 'corr_with_index_20']
        print(f"\nKey features check:")
        for feature in key_features:
            status = "✓" if feature in columns else "✗"
            print(f"  {status} {feature}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
    print("\nNote: Make sure the Flask server is running on port 5000")