from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, Response

from app.config import Settings
from app.deps import get_app_settings, get_http
from app.services.videos import random_mv

router = APIRouter(prefix="/videos/v1", tags=["videos"])


@router.get("/random")
async def random_mv_route(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
):
    mv = await random_mv.random_mv_url(client, settings)
    if mv:
        return RedirectResponse(url=mv, status_code=302)
    return Response(status_code=404)
