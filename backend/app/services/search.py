"""Search service: keyword + location → store list with parking indicators."""

import asyncio
import logging

from app.core.config import settings
from app.judge.rule_engine import JudgmentInput, judge, _has_places_parking
from app.schemas.analyze import Verdict, VehicleFit
from app.schemas.search import (
    ParkingSummary,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.sources.google_places import (
    PlaceInfo,
    search_places_nearby,
    search_nearby_parking,
)
from app.utils.geo import haversine_distance

logger = logging.getLogger(__name__)

VERDICT_LABELS = {
    Verdict.ONSITE: "駐車場あり",
    Verdict.PARTNER: "提携P",
    Verdict.NEARBY_ONLY: "近隣Pあり",
    Verdict.UNKNOWN: "P情報なし",
    Verdict.AVOID: "駐車困難",
}


async def _quick_parking_check(
    place: PlaceInfo, user_lat: float, user_lng: float
) -> ParkingSummary:
    """Lightweight parking check using Places parking options + nearby count.

    Google Places parking flag alone is NOT enough to confirm onsite parking.
    It's treated as a weak hint, combined with nearby parking availability.
    """
    has_parking = _has_places_parking(place)

    # Search nearby parking around the place
    nearby = []
    if place.lat and place.lng and settings.google_maps_api_key:
        try:
            nearby = await search_nearby_parking(place.lat, place.lng, radius_m=300)
            for p in nearby:
                if p.lat and p.lng:
                    p.distance_m = int(haversine_distance(place.lat, place.lng, p.lat, p.lng))
        except Exception as e:
            logger.warning("Quick nearby parking check failed: %s", e)

    nearby_count = len(nearby)
    nearest_dist = min((p.distance_m for p in nearby if p.distance_m > 0), default=None)

    # Google Places says parking + nearby available
    if has_parking is True and nearby_count >= 2:
        return ParkingSummary(
            verdict=Verdict.NEARBY_ONLY,
            confidence=0.4,
            vehicle_fit=VehicleFit.UNKNOWN,
            label=f"P情報あり・近隣P {nearby_count}件",
            nearby_parking_count=nearby_count,
            nearest_parking_distance_m=nearest_dist,
        )

    # Google Places says parking but no nearby context
    if has_parking is True:
        return ParkingSummary(
            verdict=Verdict.UNKNOWN,
            confidence=0.3,
            vehicle_fit=VehicleFit.UNKNOWN,
            label="P情報あり(未確認)",
            nearby_parking_count=nearby_count,
            nearest_parking_distance_m=nearest_dist,
        )

    # No parking + no nearby
    if has_parking is False and nearby_count == 0:
        return ParkingSummary(
            verdict=Verdict.AVOID,
            confidence=0.5,
            vehicle_fit=VehicleFit.UNKNOWN,
            label=VERDICT_LABELS[Verdict.AVOID],
            nearby_parking_count=0,
        )

    if nearby_count >= 2:
        return ParkingSummary(
            verdict=Verdict.NEARBY_ONLY,
            confidence=0.45,
            vehicle_fit=VehicleFit.UNKNOWN,
            label=f"近隣P {nearby_count}件",
            nearby_parking_count=nearby_count,
            nearest_parking_distance_m=nearest_dist,
        )

    if nearby_count == 1:
        return ParkingSummary(
            verdict=Verdict.NEARBY_ONLY,
            confidence=0.35,
            vehicle_fit=VehicleFit.UNKNOWN,
            label="近隣P 1件",
            nearby_parking_count=1,
            nearest_parking_distance_m=nearest_dist,
        )

    return ParkingSummary(
        verdict=Verdict.UNKNOWN,
        confidence=0.2,
        vehicle_fit=VehicleFit.UNKNOWN,
        label=VERDICT_LABELS[Verdict.UNKNOWN],
    )


async def search_with_parking(request: SearchRequest) -> SearchResponse:
    """Search for places and attach parking info to each result."""
    if not settings.google_maps_api_key:
        return SearchResponse(
            keyword=request.keyword,
            location={"lat": request.lat, "lng": request.lng},
            results=[],
            total=0,
        )

    # Step 1: Search places by keyword near location
    places = await search_places_nearby(
        keyword=request.keyword,
        lat=request.lat,
        lng=request.lng,
        radius_m=request.radius_m,
    )

    if not places:
        return SearchResponse(
            keyword=request.keyword,
            location={"lat": request.lat, "lng": request.lng},
            results=[],
            total=0,
        )

    # Step 2: For each place, run quick parking check in parallel
    async def enrich(place: PlaceInfo) -> SearchResultItem:
        parking = await _quick_parking_check(place, request.lat, request.lng)

        distance_m = None
        if place.lat and place.lng:
            distance_m = int(haversine_distance(request.lat, request.lng, place.lat, place.lng))

        return SearchResultItem(
            place_id=place.place_id,
            name=place.name,
            address=place.address or None,
            lat=place.lat,
            lng=place.lng,
            distance_m=distance_m,
            types=place.types,
            rating=place.rating,
            website_url=place.website_url,
            google_maps_uri=place.google_maps_uri,
            parking=parking,
        )

    results = await asyncio.gather(*[enrich(p) for p in places])

    # Sort by distance
    results_list = sorted(results, key=lambda r: r.distance_m or 999999)

    return SearchResponse(
        keyword=request.keyword,
        location={"lat": request.lat, "lng": request.lng},
        results=results_list,
        total=len(results_list),
    )
