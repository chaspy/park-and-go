"""Geocode / reverse-geocode endpoints.

Uses Places API (New) only — no need to enable the separate Geocoding API.
"""

import logging

import httpx

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
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
    """Resolve lat/lng to a human-readable area name using Places API (New)."""
    if not settings.google_maps_api_key:
        return ReverseGeocodeResponse(name=f"{lat:.4f}, {lng:.4f}")

    # Use Nearby Search to find the closest place and derive area from its address
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "places.formattedAddress",
    }
    body = {
        "maxResultCount": 1,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 200.0,
            }
        },
        "languageCode": "ja",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(NEARBY_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Reverse geocode via Places failed: %s", e)
            return ReverseGeocodeResponse(name=f"{lat:.4f}, {lng:.4f}")

    data = resp.json()
    places = data.get("places", [])
    if places:
        address = places[0].get("formattedAddress", "")
        if address:
            # Extract area: drop postal code and "日本、" prefix, keep up to town level
            name = address
            for prefix in ("日本、", "日本，"):
                if name.startswith(prefix):
                    name = name[len(prefix):]
            # Trim to district level (e.g. "〒167-0053 東京都杉並区西荻南３丁目" → "杉並区西荻南")
            # Remove postal code
            import re
            name = re.sub(r"〒?\d{3}-?\d{4}\s*", "", name)
            # Keep up to 丁目/番地 but drop the number part
            name = re.sub(r"[０-９0-9]+丁目.*", "", name)
            name = re.sub(r"[０-９0-9]+番.*", "", name)
            name = name.strip()
            if name:
                return ReverseGeocodeResponse(name=name)

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
