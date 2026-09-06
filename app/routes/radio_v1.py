from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.deps import get_app_settings, get_http
from app.models.response import fail, ok
from app.models.station import to_station
from app.services import radio as radio_service
from app.services.v1 import radio as radio_v1

router = APIRouter(prefix="/radio/v1", tags=["radio"])


@router.get("/play")
async def play(
    request: Request,
    keyword: str = Query(default=""),
):
    if not keyword.strip():
        return fail(400, "keyword 不能为空")
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        track = await radio_v1.resolve_radio(client, settings, keyword.strip())
    except Exception:
        return fail(502, "电台上游失败")
    if not track or not track.get("url"):
        return fail(404, f"未找到匹配电台: {keyword}")
    station = to_station(
        track,
        station_id=str(track.get("id", "")).removeprefix("radio:"),
    )
    return ok(station)


@router.get("/random")
async def random_station(request: Request):
    client = get_http(request)
    settings = get_app_settings(request)
    result = await radio_service.get_rand_radio(client, settings)
    if result.get("code") != 200:
        return fail(404, "未找到随机电台")
    return ok(to_station(result.get("data") or {}))


@router.get("/favorites")
async def favorites(request: Request):
    settings = get_app_settings(request)
    result = radio_service.get_favorite_radio(settings)
    if result.get("code") != 200:
        return fail(404, "未找到热门电台")
    return ok(to_station(result.get("data") or {}))
