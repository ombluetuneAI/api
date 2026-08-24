from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import Settings, get_settings
from app.logging_setup import get_logger, setup_logger
from app.routes import content, media, music, proxy, radio, weather

logger = get_logger(__name__)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger("logs/api.log")
    settings = get_settings()
    client = httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": UA},
    )
    app.state.settings = settings
    app.state.http = client
    logger.info("API started on port %s", settings.api_port)
    yield
    await client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="TXB API", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(weather.router)
    app.include_router(music.router)
    app.include_router(radio.router)
    app.include_router(media.router)
    app.include_router(content.router)
    app.include_router(proxy.router)
    return app


app = create_app()
