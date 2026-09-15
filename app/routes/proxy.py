from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.config import Settings
from app.deps import get_app_settings
from app.services import proxy as proxy_service

router = APIRouter(prefix="/proxy/v1", tags=["proxy"])


@router.get("/random")
async def random_proxy(settings: Settings = Depends(get_app_settings)):
    ip = proxy_service.get_random_proxy(settings.proxy_list)
    if not ip:
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ip)
