from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    ONSITE = "onsite"
    PARTNER = "partner"
    NEARBY_ONLY = "nearby_only"
    UNKNOWN = "unknown"
    AVOID = "avoid"


class VehicleFit(str, Enum):
    EASY = "easy"
    OK = "ok"
    TIGHT = "tight"
    UNKNOWN = "unknown"
    AVOID = "avoid"


class AnalyzeRequest(BaseModel):
    google_maps_url: str | None = None
    name: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    force_refresh: bool = False


class Location(BaseModel):
    lat: float
    lng: float


class EvidenceItem(BaseModel):
    source: str
    kind: str
    text: str
    weight: float = 0.0


class NearbyParkingItem(BaseModel):
    name: str
    distance_m: int
    walking_minutes: int
    lat: float | None = None
    lng: float | None = None


class AnalyzeResponse(BaseModel):
    place_key: str
    place_name: str
    address: str | None = None
    location: Location | None = None
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    vehicle_fit: VehicleFit
    summary: str
    evidence: list[EvidenceItem] = []
    nearby_parking: list[NearbyParkingItem] = []
    fetched_at: datetime


class VehicleProfile(BaseModel):
    name: str = "XC40"
    length_mm: int = 4440
    width_mm: int = 1875
    height_mm: int = 1655
    notes: str = "default user vehicle"


class ConfigResponse(BaseModel):
    vehicle: VehicleProfile
    enable_llm: bool = False
    llm_provider: str = ""
