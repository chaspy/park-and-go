"""Google Places API (New) source adapter.

Uses the Places API (New) with field masks for efficient billing.
Docs: https://developers.google.com/maps/documentation/places/web-service/op-overview
"""

import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PLACES_BASE_URL = "https://places.googleapis.com/v1/places"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

PLACE_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.types",
    "places.parkingOptions",
    "places.googleMapsUri",
    "places.rating",
]

PLACE_DETAIL_FIELDS = [
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "websiteUri",
    "nationalPhoneNumber",
    "types",
    "parkingOptions",
    "googleMapsUri",
]

TIMEOUT = 10.0


@dataclass
class PlaceInfo:
    place_id: str = ""
    name: str = ""
    address: str = ""
    lat: float | None = None
    lng: float | None = None
    website_url: str | None = None
    phone: str | None = None
    types: list[str] = field(default_factory=list)
    parking_options: dict | None = None
    google_maps_uri: str | None = None
    rating: float | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class NearbyParkingResult:
    name: str = ""
    place_id: str = ""
    lat: float | None = None
    lng: float | None = None
    distance_m: int = 0
    types: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def _get_api_key() -> str:
    key = settings.google_maps_api_key
    if not key:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set")
    return key


def _parse_place(data: dict) -> PlaceInfo:
    location = data.get("location", {})
    display_name = data.get("displayName", {})
    return PlaceInfo(
        place_id=data.get("id", ""),
        name=display_name.get("text", "") if isinstance(display_name, dict) else str(display_name),
        address=data.get("formattedAddress", ""),
        lat=location.get("latitude"),
        lng=location.get("longitude"),
        website_url=data.get("websiteUri"),
        phone=data.get("nationalPhoneNumber"),
        types=data.get("types", []),
        parking_options=data.get("parkingOptions"),
        google_maps_uri=data.get("googleMapsUri"),
        rating=data.get("rating"),
        raw=data,
    )


async def search_place(name: str, address: str | None = None) -> PlaceInfo | None:
    """Search for a place by name (and optionally address) using Text Search."""
    api_key = _get_api_key()
    query = name
    if address:
        query = f"{name} {address}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(PLACE_FIELDS),
    }
    body = {"textQuery": query, "languageCode": "ja"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(TEXT_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Places text search failed: %s", e)
            return None

    data = resp.json()
    places = data.get("places", [])
    if not places:
        logger.info("No places found for query: %s", query)
        return None

    return _parse_place(places[0])


async def search_places_nearby(
    keyword: str, lat: float, lng: float, radius_m: int = 1000, max_results: int = 10
) -> list[PlaceInfo]:
    """Search for places by keyword with location bias. Returns multiple results."""
    api_key = _get_api_key()

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(PLACE_FIELDS),
    }
    body = {
        "textQuery": keyword,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
        "maxResultCount": max_results,
        "languageCode": "ja",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(TEXT_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Places nearby text search failed: %s", e)
            return []

    data = resp.json()
    return [_parse_place(p) for p in data.get("places", [])]


async def get_place_details(place_id: str) -> PlaceInfo | None:
    """Get detailed info for a specific place by its resource name."""
    api_key = _get_api_key()
    url = f"{PLACES_BASE_URL}/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(PLACE_DETAIL_FIELDS),
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Places detail fetch failed for %s: %s", place_id, e)
            return None

    return _parse_place(resp.json())


async def search_nearby_parking(
    lat: float, lng: float, radius_m: int = 500
) -> list[NearbyParkingResult]:
    """Search for parking lots near a given location."""
    api_key = _get_api_key()

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.types",
    }
    body = {
        "includedTypes": ["parking"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
        "languageCode": "ja",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(NEARBY_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Nearby parking search failed: %s", e)
            return []

    data = resp.json()
    results: list[NearbyParkingResult] = []
    for place in data.get("places", []):
        location = place.get("location", {})
        display_name = place.get("displayName", {})
        results.append(
            NearbyParkingResult(
                name=(
                    display_name.get("text", "")
                    if isinstance(display_name, dict)
                    else str(display_name)
                ),
                place_id=place.get("id", ""),
                lat=location.get("latitude"),
                lng=location.get("longitude"),
                types=place.get("types", []),
                raw=place,
            )
        )

    return results
