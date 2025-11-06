import json
import pytest
from api import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_predict_happy_path(client):
    payload = {"ticker": "RELIANCE", "days": 3}
    resp = client.post('/api/predict', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ticker'].endswith('.NS')
    assert isinstance(data['predictions'], list)
    assert len(data['predictions']) == 3


def test_missing_ticker(client):
    payload = {"days": 3}
    resp = client.post('/api/predict', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['error'] is not None
