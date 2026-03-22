from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_with_name():
    response = client.post("/api/analyze", json={"name": "Test Store", "address": "Tokyo"})
    assert response.status_code == 200
    data = response.json()
    assert data["place_name"] == "Test Store"
    assert data["verdict"] == "unknown"
    assert data["vehicle_fit"] == "unknown"
    assert "place_key" in data


def test_analyze_with_url():
    response = client.post(
        "/api/analyze",
        json={"google_maps_url": "https://www.google.com/maps/place/TestShop/@35.0,139.0"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["place_key"] != "unknown"


def test_analyze_missing_input():
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422


def test_analyze_schema_validation():
    response = client.post("/api/analyze", json={"name": "Test", "lat": "not_a_number"})
    assert response.status_code == 422
