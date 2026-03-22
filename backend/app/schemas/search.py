from pydantic import BaseModel, Field

from app.schemas.analyze import Verdict, VehicleFit


class SearchRequest(BaseModel):
    keyword: str = Field(min_length=1, examples=["ラーメン", "ランチ", "クラフトビール"])
    lat: float
    lng: float
    radius_m: int = Field(default=1000, ge=100, le=5000)


class ParkingSummary(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    vehicle_fit: VehicleFit
    label: str  # short human-readable label
    nearby_parking_count: int = 0
    nearest_parking_distance_m: int | None = None


class SearchResultItem(BaseModel):
    place_id: str
    name: str
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    distance_m: int | None = None
    types: list[str] = []
    rating: float | None = None
    website_url: str | None = None
    google_maps_uri: str | None = None
    parking: ParkingSummary


class NearbyParkingPin(BaseModel):
    name: str
    lat: float
    lng: float
    distance_m: int


class SearchResponse(BaseModel):
    keyword: str
    location: dict
    results: list[SearchResultItem]
    nearby_parking_pins: list[NearbyParkingPin] = []
    total: int
