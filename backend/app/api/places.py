"""Endpoints for retrieving stored places and analyses."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.evidence import Evidence as EvidenceModel
from app.models.nearby_parking import NearbyParking as NearbyParkingModel
from app.models.place import Place
from app.schemas.analyze import (
    AnalyzeResponse,
    EvidenceItem,
    Location,
    NearbyParkingItem,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_response(place: Place, analysis: Analysis, db: Session) -> AnalyzeResponse:
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
                name=n.name, distance_m=n.distance_m, walking_minutes=n.walking_minutes,
                lat=n.lat, lng=n.lng,
            )
            for n in nearby
        ],
        fetched_at=analysis.fetched_at,
    )


@router.get("/api/place/{place_key}", response_model=AnalyzeResponse)
def get_place(place_key: str, db: Session = Depends(get_db)) -> AnalyzeResponse:
    place = db.query(Place).filter(Place.place_key == place_key).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    analysis = (
        db.query(Analysis)
        .filter(Analysis.place_id == place.id)
        .order_by(Analysis.fetched_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this place")

    return _build_response(place, analysis, db)


@router.get("/api/recent", response_model=list[AnalyzeResponse])
def get_recent_places(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[AnalyzeResponse]:
    """Get recently analyzed places."""
    analyses = (
        db.query(Analysis)
        .order_by(Analysis.fetched_at.desc())
        .limit(limit)
        .all()
    )

    results: list[AnalyzeResponse] = []
    seen_place_ids: set[int] = set()

    for analysis in analyses:
        if analysis.place_id in seen_place_ids:
            continue
        seen_place_ids.add(analysis.place_id)

        place = db.query(Place).filter(Place.id == analysis.place_id).first()
        if place:
            results.append(_build_response(place, analysis, db))

    return results
