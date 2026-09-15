from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.deps import get_http
from app.services.pictures import image as pictures_service

router = APIRouter(prefix="/pictures/v1", tags=["pictures"])


@router.get("/random")
async def random_pic(
    client: httpx.AsyncClient = Depends(get_http),
    w: int = Query(default=0),
    h: int = Query(default=0),
):
    image, fmt = await pictures_service.get_rand_pic(client, w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)


@router.get("/resize")
async def resize(
    client: httpx.AsyncClient = Depends(get_http),
    url: str = Query(default=""),
    w: int = Query(default=100),
    h: int = Query(default=100),
):
    image, fmt = await pictures_service.pic_resize(client, url, w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)
