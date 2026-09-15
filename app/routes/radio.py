from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query

from app.config import Settings
from app.deps import get_app_settings, get_http
from app.logging_setup import get_logger
from app.models.response import fail, ok
from app.models.station import to_station
from app.services.radio import favorites, play, random

logger = get_logger(__name__)
router = APIRouter(prefix="/radio/v1", tags=["radio"])


@router.get("/play")
async def play(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
    keyword: str = Query(default=""),
):
    if not keyword.strip():
        return fail(400, "keyword 不能为空")
    try:
        track = await play.resolve_by_name(client, settings, keyword.strip())
    except Exception:
        logger.exception("radio play failed keyword=%s", keyword)
        return fail(502, "电台上游失败")
    if not track or not track.get("url"):
        return fail(404, f"未找到匹配电台: {keyword}")
    station = to_station(
        track,
        station_id=str(track.get("id", "")).removeprefix("radio:"),
    )
    return ok(station)


@router.get("/random")
async def random_station(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
):
    try:
        data = await random.random_station(client, settings)
    except Exception:
        logger.exception("radio random failed")
        return fail(502, "电台上游失败")
    if not data or not data.get("url"):
        return fail(404, "未找到随机电台")
    return ok(to_station(data))


@router.get("/favorites")
async def favorites_route(settings: Settings = Depends(get_app_settings)):
    data = favorites.favorite_station(settings)
    if not data or not data.get("url"):
        return fail(404, "未找到热门电台")
    return ok(to_station(data))
