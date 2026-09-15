from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query

from app.config import Settings
from app.deps import get_app_settings, get_http
from app.logging_setup import get_logger
from app.models.response import fail, ok
from app.services.music import play

logger = get_logger(__name__)
router = APIRouter(prefix="/music/v1", tags=["music"])


@router.get("/search")
async def search(
    client: httpx.AsyncClient = Depends(get_http),
    keyword: str = Query(default=""),
    src: str = Query(default="kw"),
    limit: int = Query(default=10, ge=1, le=50),
):
    try:
        data = await play.search_songs(client, keyword, limit=limit, src=src)
    except Exception:
        logger.exception("music search failed keyword=%s", keyword)
        return fail(502, "搜索上游失败")
    return ok(data)


@router.get("/playlists")
async def playlists(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
    src: str = Query(default="kw"),
    limit: int = Query(default=20, ge=1, le=50),
    resolve: bool = Query(default=False),
):
    try:
        data = await play.get_playlists(
            client, settings, src=src, limit=limit, resolve=resolve
        )
    except Exception:
        logger.exception("music playlists failed src=%s", src)
        return fail(502, "歌单读取失败")
    return ok(data)


@router.get("/play")
async def play_song(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
    keyword: str = Query(default=""),
    id: str = Query(default=""),
    src: str = Query(default="kw"),
    mid: str = Query(default=""),
    source: str = Query(default="auto"),
    quality: str = Query(default="320k"),
):
    if not keyword.strip() and not id.strip() and not mid.strip():
        return fail(400, "keyword 或 id 不能为空")
    try:
        song = await play.play_song(
            client,
            settings,
            keyword=keyword,
            song_id=id,
            src=src,
            mid=mid,
            source=source,
            quality=quality,
        )
    except Exception:
        logger.exception("music play failed")
        return fail(502, "取流失败")
    if not song or not song.get("url"):
        return fail(404, "未找到可播放曲目")
    return ok(song)


@router.get("/random")
async def random_song(
    client: httpx.AsyncClient = Depends(get_http),
    settings: Settings = Depends(get_app_settings),
    src: str = Query(default="kw"),
):
    try:
        song = await play.random_song(client, settings, src=src)
    except Exception:
        logger.exception("music random failed src=%s", src)
        return fail(502, "随机取流失败")
    if not song or not song.get("url"):
        return fail(404, "当前没有可随机的曲目")
    return ok(song)
