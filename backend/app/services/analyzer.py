"""Analysis orchestrator service.

Coordinates data collection from sources, runs judgment, and handles caching.
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.judge.llm_judge import LLMExtractionRequest, get_llm_extractor
from app.judge.rule_engine import JudgmentInput, judge
from app.models.analysis import Analysis
from app.models.evidence import Evidence as EvidenceModel
from app.models.nearby_parking import NearbyParking as NearbyParkingModel
from app.models.place import Place
from app.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceItem,
    Location,
    NearbyParkingItem,
)
from app.sources.google_places import (
    PlaceInfo,
    search_nearby_parking,
    search_place,
)
from app.sources.official_site import SiteScrapingResult, scrape_site
from app.utils.geo import haversine_distance, walking_minutes
from app.utils.place_key import normalize_place_key

logger = logging.getLogger(__name__)


def _get_cached_analysis(db: Session, place_key: str) -> Analysis | None:
    """Get the most recent analysis for a place if it exists and is fresh."""
    place = db.query(Place).filter(Place.place_key == place_key).first()
    if not place:
        return None

    analysis = (
        db.query(Analysis)
        .filter(Analysis.place_id == place.id)
        .order_by(Analysis.fetched_at.desc())
        .first()
    )
    if not analysis:
        return None

    age_hours = (datetime.now(timezone.utc) - analysis.fetched_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    if age_hours > settings.cache_ttl_hours:
        return None

    return analysis


def _analysis_to_response(place: Place, analysis: Analysis, db: Session) -> AnalyzeResponse:
    """Convert DB models to response schema."""
    evidences = db.query(EvidenceModel).filter(EvidenceModel.analysis_id == analysis.id).all()
    nearby = db.query(NearbyParkingModel).filter(NearbyParkingModel.analysis_id == analysis.id).all()

    return AnalyzeResponse(
        place_key=place.place_key,
        place_name=place.name,
        address=place.address,
        location=Location(lat=place.lat, lng=place.lng) if place.lat and place.lng else None,
        verdict=analysis.verdict,
        confidence=analysis.confidence,
        vehicle_fit=analysis.vehicle_fit,
        summary=analysis.summary,
        evidence=[
            EvidenceItem(source=e.source, kind=e.kind, text=e.text, weight=e.weight)
            for e in evidences
        ],
        nearby_parking=[
            NearbyParkingItem(
                name=n.name,
                distance_m=n.distance_m,
                walking_minutes=n.walking_minutes,
                lat=n.lat,
                lng=n.lng,
            )
            for n in nearby
        ],
        fetched_at=analysis.fetched_at,
    )


def _save_analysis(
    db: Session,
    place_key: str,
    place_info: PlaceInfo | None,
    request: AnalyzeRequest,
    judgment_result,
    nearby_items: list[NearbyParkingItem],
) -> tuple[Place, Analysis]:
    """Persist analysis results to database."""
    # Upsert place
    place = db.query(Place).filter(Place.place_key == place_key).first()
    if not place:
        place = Place(place_key=place_key)

    place.name = (place_info.name if place_info else request.name) or "Unknown"
    place.address = (place_info.address if place_info else request.address) or None
    if place_info:
        place.place_id = place_info.place_id
        place.lat = place_info.lat
        place.lng = place_info.lng
        place.website_url = place_info.website_url
        place.raw_json = json.dumps(place_info.raw, ensure_ascii=False) if place_info.raw else None
    elif request.lat and request.lng:
        place.lat = request.lat
        place.lng = request.lng
    place.updated_at = datetime.now(timezone.utc)

    db.add(place)
    db.flush()

    # Create analysis
    analysis = Analysis(
        place_id=place.id,
        verdict=judgment_result.verdict.value,
        confidence=judgment_result.confidence,
        vehicle_fit=judgment_result.vehicle_fit.value,
        summary=judgment_result.summary,
        raw_result_json=json.dumps(
            {"evidence_count": len(judgment_result.evidence)}, ensure_ascii=False
        ),
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(analysis)
    db.flush()

    # Save evidence
    for ev in judgment_result.evidence:
        db.add(EvidenceModel(
            analysis_id=analysis.id,
            source=ev.source,
            kind=ev.kind,
            text=ev.text,
            weight=ev.weight,
        ))

    # Save nearby parking
    for np in nearby_items:
        db.add(NearbyParkingModel(
            analysis_id=analysis.id,
            name=np.name,
            distance_m=np.distance_m,
            walking_minutes=np.walking_minutes,
            lat=np.lat,
            lng=np.lng,
        ))

    db.commit()
    return place, analysis


def _has_useful_mentions(site_result: SiteScrapingResult | None) -> bool:
    """Check if regex extraction found any parking-related mentions."""
    if not site_result:
        return False
    return len(site_result.mentions) > 0


async def _run_llm_extraction(
    place_name: str, site_result: SiteScrapingResult | None
) -> SiteScrapingResult | None:
    """Run LLM extraction on site text when regex found nothing."""
    extractor = get_llm_extractor()
    if not extractor.is_available():
        return site_result

    if not site_result or not site_result.url:
        return site_result

    # Build text from all scraped pages for LLM
    # We already have the mentions list, but the raw text isn't stored.
    # Re-fetch the main page text for LLM. This is a trade-off:
    # we could cache it, but for now we re-extract from the URL.
    from app.sources.official_site import _extract_text

    import httpx as _httpx
    try:
        async with _httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                site_result.url,
                headers={"User-Agent": "parking-judge/0.1 (personal use)"},
            )
            if resp.status_code != 200:
                return site_result
            site_text = _extract_text(resp.text[:500_000])
    except Exception as e:
        logger.warning("Failed to re-fetch site for LLM: %s", e)
        return site_result

    logger.info("Running LLM extraction for %s (%d chars)", place_name, len(site_text))

    request = LLMExtractionRequest(place_name=place_name, site_text=site_text)
    result = await extractor.extract(request)

    if result is None:
        return site_result

    # Convert LLM output to mentions and append to site_result
    llm_mentions = result.to_mentions()
    if llm_mentions:
        logger.info("LLM found %d parking mentions for %s", len(llm_mentions), place_name)
        if site_result is None:
            site_result = SiteScrapingResult(url="")
        site_result.mentions.extend(llm_mentions)

    return site_result


async def analyze_place(request: AnalyzeRequest, db: Session) -> AnalyzeResponse:
    """Main analysis pipeline."""
    place_key = normalize_place_key(
        name=request.name,
        address=request.address,
        google_maps_url=request.google_maps_url,
    )

    # Check cache
    if not request.force_refresh:
        cached = _get_cached_analysis(db, place_key)
        if cached:
            place = db.query(Place).filter(Place.place_key == place_key).first()
            logger.info("Cache hit for place_key=%s", place_key)
            return _analysis_to_response(place, cached, db)

    logger.info("Running fresh analysis for place_key=%s", place_key)

    # Step 1: Resolve place via Google Places
    place_info: PlaceInfo | None = None
    if settings.google_maps_api_key:
        try:
            place_info = await search_place(
                name=request.name or "",
                address=request.address,
            )
        except Exception as e:
            logger.warning("Google Places search failed: %s", e)

    # Step 2: Scrape official site
    site_result = None
    website_url = place_info.website_url if place_info else None
    if website_url:
        try:
            site_result = await scrape_site(website_url)
        except Exception as e:
            logger.warning("Site scraping failed for %s: %s", website_url, e)

    # Step 2.5: If regex found nothing useful, try LLM extraction
    if not _has_useful_mentions(site_result) and website_url:
        try:
            site_result = await _run_llm_extraction(
                place_name=(place_info.name if place_info else request.name) or "Unknown",
                site_result=site_result,
            )
        except Exception as e:
            logger.warning("LLM extraction failed: %s", e)

    # Step 3: Search nearby parking
    lat = (place_info.lat if place_info else request.lat) or None
    lng = (place_info.lng if place_info else request.lng) or None

    nearby_raw = []
    if lat and lng and settings.google_maps_api_key:
        try:
            nearby_raw = await search_nearby_parking(lat, lng, radius_m=500)
        except Exception as e:
            logger.warning("Nearby parking search failed: %s", e)

    # Compute distances for nearby parking
    nearby_items: list[NearbyParkingItem] = []
    for p in nearby_raw:
        if p.lat and p.lng and lat and lng:
            dist = int(haversine_distance(lat, lng, p.lat, p.lng))
            p.distance_m = dist
            nearby_items.append(NearbyParkingItem(
                name=p.name,
                distance_m=dist,
                walking_minutes=walking_minutes(dist),
                lat=p.lat,
                lng=p.lng,
            ))

    nearby_items.sort(key=lambda x: x.distance_m)

    # Step 4: Run judgment
    judgment_input = JudgmentInput(
        place_info=place_info,
        site_result=site_result,
        nearby_parking=nearby_raw,
    )
    judgment_result = judge(judgment_input)

    # Step 5: Save to DB
    try:
        place, analysis = _save_analysis(
            db, place_key, place_info, request, judgment_result, nearby_items
        )
    except Exception as e:
        logger.error("Failed to save analysis: %s", e)
        db.rollback()
        return AnalyzeResponse(
            place_key=place_key,
            place_name=(place_info.name if place_info else request.name) or "Unknown",
            address=(place_info.address if place_info else request.address),
            location=Location(lat=lat, lng=lng) if lat and lng else None,
            verdict=judgment_result.verdict,
            confidence=judgment_result.confidence,
            vehicle_fit=judgment_result.vehicle_fit,
            summary=judgment_result.summary,
            evidence=judgment_result.evidence,
            nearby_parking=nearby_items,
            fetched_at=datetime.now(timezone.utc),
        )

    return _analysis_to_response(place, analysis, db)
