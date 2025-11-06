import json
import pytest
from app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_health_check(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'healthy'


def test_predict_happy_path(client):
    # Use manual mode to avoid external API dependency during tests
    payload = {
        "ticker": "RELIANCE",
        "days": 3,
        "mode": "manual",
        "base_price": 2500,
        "drift_pct": 0.1,
        "vol_pct": 0.2,
        "slope": 1.0,
    }
    resp = client.post('/api/predict', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data['ticker'], str) and len(data['ticker']) > 0
    assert isinstance(data['predictions'], list)
    assert len(data['predictions']) == 3


def test_missing_ticker(client):
    payload = {"days": 3}
    resp = client.post('/api/predict', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['error'] is not None


def test_manual_mode_prediction(client):
    payload = {
        "ticker": "TCS",
        "days": 4,
        "mode": "manual",
        "base_price": 1000,
        "drift_pct": 0.2,  # 0.2% per step
        "vol_pct": 0.5,    # 0.5% stddev noise
        "slope": 2.0       # +2 INR per step
    }
    resp = client.post('/api/predict', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data['ticker'], str) and len(data['ticker']) > 0
    assert isinstance(data['predictions'], list)
    assert len(data['predictions']) == 4