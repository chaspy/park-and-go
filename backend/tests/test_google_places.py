import pytest
import httpx

from app.sources.google_places import (
    search_place,
    search_nearby_parking,
    _parse_place,
)

DUMMY_REQUEST = httpx.Request("POST", "https://test.example.com")


def test_parse_place():
    data = {
        "id": "ChIJ_test",
        "displayName": {"text": "Test Shop"},
        "formattedAddress": "Tokyo, Shibuya",
        "location": {"latitude": 35.6, "longitude": 139.7},
        "websiteUri": "https://example.com",
        "nationalPhoneNumber": "03-1234-5678",
        "types": ["restaurant"],
        "parkingOptions": {"freeParkingLot": True},
        "googleMapsUri": "https://maps.google.com/?cid=123",
    }
    info = _parse_place(data)
    assert info.place_id == "ChIJ_test"
    assert info.name == "Test Shop"
    assert info.lat == 35.6
    assert info.lng == 139.7
    assert info.website_url == "https://example.com"
    assert info.parking_options == {"freeParkingLot": True}


def test_parse_place_minimal():
    data = {"id": "ChIJ_min", "displayName": {"text": "Min"}}
    info = _parse_place(data)
    assert info.place_id == "ChIJ_min"
    assert info.name == "Min"
    assert info.lat is None
    assert info.parking_options is None


@pytest.mark.asyncio
async def test_search_place_success(monkeypatch):
    response_json = {
        "places": [
            {
                "id": "ChIJ_found",
                "displayName": {"text": "Found Store"},
                "formattedAddress": "Shibuya",
                "location": {"latitude": 35.6, "longitude": 139.7},
                "types": ["store"],
            }
        ]
    }

    async def mock_post(self, url, **kwargs):
        return httpx.Response(200, json=response_json, request=DUMMY_REQUEST)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr("app.sources.google_places.settings.google_maps_api_key", "test-key")

    result = await search_place("Found Store", "Shibuya")
    assert result is not None
    assert result.name == "Found Store"
    assert result.place_id == "ChIJ_found"


@pytest.mark.asyncio
async def test_search_place_no_results(monkeypatch):
    async def mock_post(self, url, **kwargs):
        return httpx.Response(200, json={"places": []}, request=DUMMY_REQUEST)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr("app.sources.google_places.settings.google_maps_api_key", "test-key")

    result = await search_place("Nonexistent Store")
    assert result is None


@pytest.mark.asyncio
async def test_search_nearby_parking(monkeypatch):
    response_json = {
        "places": [
            {
                "id": "parking1",
                "displayName": {"text": "Times Shibuya"},
                "location": {"latitude": 35.601, "longitude": 139.701},
                "types": ["parking"],
            }
        ]
    }

    async def mock_post(self, url, **kwargs):
        return httpx.Response(200, json=response_json, request=DUMMY_REQUEST)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr("app.sources.google_places.settings.google_maps_api_key", "test-key")

    results = await search_nearby_parking(35.6, 139.7, radius_m=300)
    assert len(results) == 1
    assert results[0].name == "Times Shibuya"


@pytest.mark.asyncio
async def test_search_place_api_error(monkeypatch):
    async def mock_post(self, url, **kwargs):
        return httpx.Response(500, json={"error": "internal"}, request=DUMMY_REQUEST)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr("app.sources.google_places.settings.google_maps_api_key", "test-key")

    result = await search_place("Test")
    assert result is None
