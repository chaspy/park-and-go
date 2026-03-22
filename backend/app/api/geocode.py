"""Geocode / reverse-geocode endpoints."""

import logging

import httpx

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TIMEOUT = 10.0


class GeocodeRequest(BaseModel):
    query: str


class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    name: str


class ReverseGeocodeResponse(BaseModel):
    name: str


@router.get("/api/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode(
    lat: float = Query(...),
    lng: float = Query(...),
) -> ReverseGeocodeResponse:
    """Resolve lat/lng to a human-readable place name."""
    if not settings.google_maps_api_key:
        return ReverseGeocodeResponse(name=f"{lat:.4f}, {lng:.4f}")

    params = {
        "latlng": f"{lat},{lng}",
        "key": settings.google_maps_api_key,
        "language": "ja",
        "result_type": "sublocality|locality|administrative_area_level_3",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(GEOCODE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Reverse geocode failed: %s", e)
            return ReverseGeocodeResponse(name=f"{lat:.4f}, {lng:.4f}")

    data = resp.json()
    results = data.get("results", [])
    if results:
        return ReverseGeocodeResponse(name=results[0].get("formatted_address", f"{lat:.4f}, {lng:.4f}"))

    return ReverseGeocodeResponse(name=f"{lat:.4f}, {lng:.4f}")


@router.post("/api/geocode", response_model=GeocodeResponse)
async def geocode(request: GeocodeRequest) -> GeocodeResponse:
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail="Google Maps API key not configured")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "places.location,places.displayName",
    }
    body = {"textQuery": request.query, "maxResultCount": 1, "languageCode": "ja"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(TEXT_SEARCH_URL, headers=headers, json=body)
        resp.raise_for_status()

    data = resp.json()
    places = data.get("places", [])
    if not places:
        raise HTTPException(status_code=404, detail="場所が見つかりませんでした")

    place = places[0]
    loc = place.get("location", {})
    display_name = place.get("displayName", {})

    return GeocodeResponse(
        lat=loc["latitude"],
        lng=loc["longitude"],
        name=display_name.get("text", request.query) if isinstance(display_name, dict) else request.query,
    )
