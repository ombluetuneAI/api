from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from app.deps import get_http
from app.models.response import ok
from app.services.content import dailyhot

router = APIRouter(prefix="/content/v1", tags=["content"])


@router.get("/dailyhot")
async def dailyhot_route(client: httpx.AsyncClient = Depends(get_http)):
    news, update_time = await dailyhot.fetch_dailyhot(client)
    return ok({"list": news, "updateTime": update_time})
