from fastapi import APIRouter

from app.core.config import settings
from app.schemas.analyze import ConfigResponse, VehicleProfile

router = APIRouter()


@router.get("/api/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        vehicle=VehicleProfile(
            name=settings.vehicle_name,
            length_mm=settings.vehicle_length_mm,
            width_mm=settings.vehicle_width_mm,
            height_mm=settings.vehicle_height_mm,
        ),
        enable_llm=settings.enable_llm,
        llm_provider=settings.llm_provider,
    )
