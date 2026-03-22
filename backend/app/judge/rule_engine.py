"""Rule-based parking verdict engine.

Produces a verdict (onsite/partner/nearby_only/unknown/avoid) and vehicle fit
based on evidence collected from Google Places API and official site scraping.
"""

import logging
from dataclasses import dataclass, field

from app.schemas.analyze import EvidenceItem, Verdict, VehicleFit
from app.sources.google_places import PlaceInfo, NearbyParkingResult
from app.sources.official_site import ParkingMention, SiteScrapingResult
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class JudgmentInput:
    place_info: PlaceInfo | None = None
    site_result: SiteScrapingResult | None = None
    nearby_parking: list[NearbyParkingResult] = field(default_factory=list)


@dataclass
class JudgmentResult:
    verdict: Verdict = Verdict.UNKNOWN
    confidence: float = 0.0
    vehicle_fit: VehicleFit = VehicleFit.UNKNOWN
    summary: str = ""
    evidence: list[EvidenceItem] = field(default_factory=list)


def _has_places_parking(place_info: PlaceInfo | None) -> bool | None:
    """Check if Google Places indicates parking availability."""
    if not place_info or not place_info.parking_options:
        return None
    opts = place_info.parking_options
    # Any truthy parking option means parking exists
    for key in ("freeParkingLot", "paidParkingLot", "freeStreetParking",
                "paidStreetParking", "valetParking", "freeGarageParking",
                "paidGarageParking"):
        if opts.get(key) is True:
            return True
    # If all are explicitly false, that's a signal too
    if any(opts.get(k) is False for k in opts):
        return False
    return None


def _collect_site_evidence(
    site_result: SiteScrapingResult | None,
) -> tuple[list[EvidenceItem], list[ParkingMention]]:
    """Convert site scraping mentions to evidence items."""
    evidence: list[EvidenceItem] = []
    mentions: list[ParkingMention] = []

    if not site_result:
        return evidence, mentions

    for mention in site_result.mentions:
        mentions.append(mention)
        weight_map = {
            "positive": 0.7,
            "partner": 0.7,
            "negative": 0.8,
            "capacity": 0.6,
            "height_limit": 0.5,
            "width_limit": 0.5,
            "tight": 0.5,
        }
        evidence.append(EvidenceItem(
            source="official_site",
            kind=f"text_match_{mention.kind}",
            text=mention.context,
            weight=weight_map.get(mention.kind, 0.3),
        ))

    return evidence, mentions


def _count_nearby(nearby: list[NearbyParkingResult], max_distance_m: int) -> int:
    """Count nearby parking results within a given distance."""
    return sum(1 for p in nearby if p.distance_m <= max_distance_m)


def _evaluate_vehicle_fit(
    mentions: list[ParkingMention],
) -> VehicleFit:
    """Evaluate whether the user's vehicle fits based on mentions."""
    vehicle_height_m = settings.vehicle_height_mm / 1000.0
    vehicle_width_m = settings.vehicle_width_mm / 1000.0

    for mention in mentions:
        if mention.kind == "height_limit" and mention.value:
            try:
                limit = float(mention.value)
                # Normalize: if limit > 10, assume mm or cm
                if limit > 100:
                    limit = limit / 1000.0
                elif limit > 10:
                    limit = limit / 100.0
                if vehicle_height_m > limit:
                    return VehicleFit.AVOID
                if vehicle_height_m > limit - 0.05:
                    return VehicleFit.TIGHT
            except ValueError:
                pass

        if mention.kind == "width_limit" and mention.value:
            try:
                limit = float(mention.value)
                if limit > 100:
                    limit = limit / 1000.0
                elif limit > 10:
                    limit = limit / 100.0
                if vehicle_width_m > limit:
                    return VehicleFit.AVOID
                if vehicle_width_m > limit - 0.05:
                    return VehicleFit.TIGHT
            except ValueError:
                pass

        if mention.kind == "tight":
            return VehicleFit.TIGHT

    return VehicleFit.UNKNOWN


def judge(input_data: JudgmentInput) -> JudgmentResult:
    """Run rule-based judgment and return a result."""
    result = JudgmentResult()
    all_evidence: list[EvidenceItem] = []

    # --- Google Places parking ---
    places_parking = _has_places_parking(input_data.place_info)
    if places_parking is True:
        all_evidence.append(EvidenceItem(
            source="google_places",
            kind="parking_option",
            text="Google Places indicates parking is available",
            weight=0.6,
        ))
    elif places_parking is False:
        all_evidence.append(EvidenceItem(
            source="google_places",
            kind="parking_option",
            text="Google Places indicates no parking options",
            weight=0.4,
        ))
    else:
        all_evidence.append(EvidenceItem(
            source="google_places",
            kind="parking_option",
            text="No parking information from Google Places",
            weight=0.1,
        ))

    # --- Official site ---
    site_evidence, mentions = _collect_site_evidence(input_data.site_result)
    all_evidence.extend(site_evidence)

    has_positive = any(m.kind == "positive" for m in mentions)
    has_partner = any(m.kind == "partner" for m in mentions)
    has_negative = any(m.kind == "negative" for m in mentions)
    has_capacity = any(m.kind == "capacity" for m in mentions)

    # --- Nearby parking ---
    nearby_150 = _count_nearby(input_data.nearby_parking, 150)
    nearby_300 = _count_nearby(input_data.nearby_parking, 300)
    nearby_500 = _count_nearby(input_data.nearby_parking, 500)

    if input_data.nearby_parking:
        all_evidence.append(EvidenceItem(
            source="nearby_search",
            kind="parking_count",
            text=f"Nearby parking: {nearby_150} within 150m, {nearby_300} within 300m, {nearby_500} within 500m",
            weight=0.3,
        ))

    # --- Derived flags ---
    site_says_nothing = not has_positive and not has_negative and not has_partner

    # --- Rule-based decision ---

    # Rule 1a: Places parking + site confirms → onsite, high confidence
    if places_parking is True and has_positive:
        result.verdict = Verdict.ONSITE
        result.confidence = 0.8 if has_capacity else 0.75
        result.summary = "Google Placesおよび公式サイトの両方で駐車場ありの情報が確認できました。"

    # Rule 1b: Places parking + site says nothing → weak signal, not enough to confirm
    elif places_parking is True and site_says_nothing:
        if nearby_150 >= 2:
            result.verdict = Verdict.NEARBY_ONLY
            result.confidence = 0.4
            result.summary = (
                f"Google Placesに駐車場情報がありますが、公式サイトでは確認できませんでした。"
                f"150m以内に{nearby_150}件の近隣駐車場があります。"
            )
        else:
            result.verdict = Verdict.UNKNOWN
            result.confidence = 0.35
            result.summary = (
                "Google Placesに駐車場ありの情報がありますが、公式サイトでは確認できませんでした。"
                "実際に駐車場があるかは不明です。"
            )

    # Rule 1c: Places parking + site denies → site denial wins
    elif places_parking is True and has_negative:
        if nearby_300 > 0:
            result.verdict = Verdict.NEARBY_ONLY
            result.confidence = 0.6
            result.summary = (
                f"公式サイトでは駐車場なしの記載があります。300m以内に{nearby_300}件の駐車場候補があります。"
            )
        else:
            result.verdict = Verdict.AVOID
            result.confidence = 0.55
            result.summary = "公式サイトに駐車場なしの記載があります。"

    # Rule 2: Site says partner
    elif has_partner:
        result.verdict = Verdict.PARTNER
        result.confidence = 0.75
        result.summary = "提携駐車場があるようです。"

    # Rule 3: Site says positive (even without Places)
    elif has_positive and not has_negative:
        result.verdict = Verdict.ONSITE
        result.confidence = 0.7 if has_capacity else 0.6
        result.summary = "公式サイトに駐車場ありの記載が見つかりました。"

    # Rule 4: Site says negative + nearby available
    elif has_negative and nearby_300 > 0:
        result.verdict = Verdict.NEARBY_ONLY
        result.confidence = 0.7
        result.summary = (
            f"店専用駐車場はないようですが、300m以内に{nearby_300}件の駐車場候補があります。"
        )

    # Rule 5: Site says negative + no nearby
    elif has_negative and nearby_500 == 0:
        result.verdict = Verdict.AVOID
        result.confidence = 0.6
        result.summary = "駐車場なしの記載があり、近隣にも駐車場が見つかりませんでした。"

    # Rule 6: No info but nearby parking exists
    elif not has_positive and not has_negative and nearby_150 >= 2:
        result.verdict = Verdict.NEARBY_ONLY
        result.confidence = 0.45
        result.summary = (
            f"駐車場の明示はありませんが、150m以内に{nearby_150}件の駐車場候補があります。"
        )

    # Rule 7: No info, some nearby
    elif not has_positive and not has_negative and nearby_500 > 0:
        result.verdict = Verdict.NEARBY_ONLY
        result.confidence = 0.35
        result.summary = (
            f"駐車場の明示はありませんが、500m以内に{nearby_500}件の駐車場候補があります。"
        )

    # Default: unknown
    else:
        result.verdict = Verdict.UNKNOWN
        result.confidence = 0.2
        result.summary = "駐車場情報を十分に確認できませんでした。"

    # --- Vehicle fit ---
    result.vehicle_fit = _evaluate_vehicle_fit(mentions)

    result.evidence = all_evidence

    # Clamp confidence
    result.confidence = max(0.0, min(1.0, result.confidence))

    return result
