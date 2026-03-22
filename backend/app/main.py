import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.analyze import router as analyze_router
from app.api.config import router as config_router
from app.api.health import router as health_router
from app.api.places import router as places_router
from app.api.geocode import router as geocode_router
from app.api.search import router as search_router
from app.db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

WEB_DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Initializing database...")
    init_db()
    logger.info("parking-judge started")
    if WEB_DIST.exists():
        logger.info("Serving Web UI from %s", WEB_DIST)
    else:
        logger.warning("Web UI not found at %s — run 'cd web && npm run build'", WEB_DIST)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="parking-judge", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(analyze_router)
    app.include_router(config_router)
    app.include_router(places_router)
    app.include_router(search_router)
    app.include_router(geocode_router)

    # Serve built Web UI as static files (must be after API routes)
    if WEB_DIST.exists():
        app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")

    return app


app = create_app()
