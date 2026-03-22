import logging

from fastapi import APIRouter

from app.schemas.search import SearchRequest, SearchResponse
from app.services.search import search_with_parking

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return await search_with_parking(request)
