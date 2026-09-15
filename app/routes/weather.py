from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query

from app.config import Settings
from app.deps import get_app_settings, get_http
from app.models.response import fail, ok
from app.services import weather as weather_service

router = APIRouter(prefix="/weather/v1", tags=["weather"])


@router.get("/current")
async def current(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
):
    data = await weather_service.get_current(client, settings)
    return ok(data)


@router.get("/proxy")
async def proxy(
    client: httpx.AsyncClient = Depends(get_http),
    url: str = Query(default=""),
):
    target = url.strip()
    if not target:
        return fail(400, "missing url")
    data = await weather_service.fetch_proxy_url(client, target)
    return ok(data)
