from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.constants import DEFAULT_UA
from app.logging_setup import get_logger, setup_logger
from app.routes import content, music, pictures, proxy, radio, videos, weather

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger("logs/api.log")
    settings = get_settings()
    client = httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_UA},
    )
    app.state.settings = settings
    app.state.http = client
    logger.info("API started on port %s", settings.api_port)
    yield
    await client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app_kwargs: dict = {
        "title": "TXB API",
        "version": "2.2.0",
        "lifespan": lifespan,
    }
    if settings.api_root_path:
        app_kwargs["root_path"] = settings.api_root_path
    app = FastAPI(**app_kwargs)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(music.router)
    app.include_router(radio.router)
    app.include_router(pictures.router)
    app.include_router(videos.router)
    app.include_router(content.router)
    app.include_router(weather.router)
    app.include_router(proxy.router)

    return app


app = create_app()
