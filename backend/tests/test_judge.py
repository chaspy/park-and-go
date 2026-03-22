"""Table-driven tests for the rule-based judgment engine."""

import pytest

from app.judge.rule_engine import JudgmentInput, judge
from app.schemas.analyze import Verdict, VehicleFit
from app.sources.google_places import PlaceInfo, NearbyParkingResult
from app.sources.official_site import ParkingMention, SiteScrapingResult


def _site_with_mentions(*mentions: ParkingMention) -> SiteScrapingResult:
    return SiteScrapingResult(url="https://example.com", mentions=list(mentions))


def _mention(kind: str, text: str = "", value: str | None = None) -> ParkingMention:
    return ParkingMention(text=text, context=text, kind=kind, value=value)


def _nearby(n: int, distance_m: int = 100) -> list[NearbyParkingResult]:
    return [
        NearbyParkingResult(name=f"Parking {i}", distance_m=distance_m)
        for i in range(n)
    ]


class TestVerdict:
    """Table-driven verdict tests."""

    @pytest.mark.parametrize(
        "description, input_data, expected_verdict",
        [
            (
                "Places parking + site says nothing → unknown (Google alone is weak)",
                JudgmentInput(
                    place_info=PlaceInfo(parking_options={"freeParkingLot": True}),
                ),
                Verdict.UNKNOWN,
            ),
            (
                "Places parking + site says nothing + nearby → nearby_only",
                JudgmentInput(
                    place_info=PlaceInfo(parking_options={"freeParkingLot": True}),
                    nearby_parking=_nearby(3, distance_m=100),
                ),
                Verdict.NEARBY_ONLY,
            ),
            (
                "Places parking + site positive → onsite high confidence",
                JudgmentInput(
                    place_info=PlaceInfo(parking_options={"freeParkingLot": True}),
                    site_result=_site_with_mentions(_mention("positive", "駐車場あり")),
                ),
                Verdict.ONSITE,
            ),
            (
                "Places parking + site negative → site denial wins",
                JudgmentInput(
                    place_info=PlaceInfo(parking_options={"freeParkingLot": True}),
                    site_result=_site_with_mentions(_mention("negative", "駐車場なし")),
                    nearby_parking=_nearby(2, distance_m=200),
                ),
                Verdict.NEARBY_ONLY,
            ),
            (
                "Site says 提携駐車場 → partner",
                JudgmentInput(
                    site_result=_site_with_mentions(_mention("partner", "提携駐車場あり")),
                ),
                Verdict.PARTNER,
            ),
            (
                "Site positive only → onsite",
                JudgmentInput(
                    site_result=_site_with_mentions(_mention("positive", "駐車場あり")),
                ),
                Verdict.ONSITE,
            ),
            (
                "Site negative + nearby parking → nearby_only",
                JudgmentInput(
                    site_result=_site_with_mentions(_mention("negative", "駐車場なし")),
                    nearby_parking=_nearby(2, distance_m=200),
                ),
                Verdict.NEARBY_ONLY,
            ),
            (
                "Site negative + no nearby → avoid",
                JudgmentInput(
                    site_result=_site_with_mentions(_mention("negative", "駐車場なし")),
                    nearby_parking=[],
                ),
                Verdict.AVOID,
            ),
            (
                "No info + 150m内に複数parking → nearby_only",
                JudgmentInput(
                    nearby_parking=_nearby(3, distance_m=100),
                ),
                Verdict.NEARBY_ONLY,
            ),
            (
                "No info + no nearby → unknown",
                JudgmentInput(),
                Verdict.UNKNOWN,
            ),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_verdict(self, description, input_data, expected_verdict):
        result = judge(input_data)
        assert result.verdict == expected_verdict, (
            f"{description}: expected {expected_verdict}, got {result.verdict}"
        )

    def test_confidence_range(self):
        result = judge(JudgmentInput())
        assert 0.0 <= result.confidence <= 1.0

    def test_evidence_always_present(self):
        result = judge(JudgmentInput())
        assert len(result.evidence) >= 1


class TestVehicleFit:
    def test_height_limit_avoid(self, monkeypatch):
        monkeypatch.setattr("app.judge.rule_engine.settings.vehicle_height_mm", 1655)
        input_data = JudgmentInput(
            site_result=_site_with_mentions(
                _mention("positive", "駐車場あり"),
                _mention("height_limit", "車高制限: 1.55m", value="1.55"),
            ),
        )
        result = judge(input_data)
        assert result.vehicle_fit == VehicleFit.AVOID

    def test_height_limit_tight(self, monkeypatch):
        monkeypatch.setattr("app.judge.rule_engine.settings.vehicle_height_mm", 1650)
        input_data = JudgmentInput(
            site_result=_site_with_mentions(
                _mention("positive", "駐車場あり"),
                _mention("height_limit", "車高制限: 1.68m", value="1.68"),
            ),
        )
        result = judge(input_data)
        assert result.vehicle_fit == VehicleFit.TIGHT

    def test_width_limit_avoid(self, monkeypatch):
        monkeypatch.setattr("app.judge.rule_engine.settings.vehicle_width_mm", 1875)
        input_data = JudgmentInput(
            site_result=_site_with_mentions(
                _mention("positive", "駐車場あり"),
                _mention("width_limit", "車幅制限: 1.80m", value="1.80"),
            ),
        )
        result = judge(input_data)
        assert result.vehicle_fit == VehicleFit.AVOID

    def test_tight_keyword(self):
        input_data = JudgmentInput(
            site_result=_site_with_mentions(
                _mention("positive", "駐車場あり"),
                _mention("tight", "1台のみ"),
            ),
        )
        result = judge(input_data)
        assert result.vehicle_fit == VehicleFit.TIGHT

    def test_no_limit_info(self):
        input_data = JudgmentInput(
            site_result=_site_with_mentions(_mention("positive", "駐車場あり")),
        )
        result = judge(input_data)
        assert result.vehicle_fit == VehicleFit.UNKNOWN
