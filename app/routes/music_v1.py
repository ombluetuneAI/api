from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.deps import get_app_settings, get_http
from app.models.response import fail, ok
from app.services import music_play

router = APIRouter(prefix="/music/v1", tags=["music"])


@router.get("/search")
async def search(
    request: Request,
    keyword: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=50),
):
    client = get_http(request)
    try:
        items = await music_play.search_songs(client, keyword, limit=limit)
    except Exception:
        return fail(502, "搜索上游失败")
    return ok({"list": items, "total": len(items)})


@router.get("/playlists")
async def playlists(
    request: Request,
    src: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
    resolve: bool = Query(default=False),
):
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        data = await music_play.get_playlists(
            client, settings, src=src, limit=limit, resolve=resolve
        )
    except Exception:
        return fail(502, "歌单读取失败")
    return ok(data)


@router.get("/songs/play")
async def songs_play(
    request: Request,
    keyword: str = Query(default=""),
    id: str = Query(default=""),
    src: str = Query(default=""),
    mid: str = Query(default=""),
    source: str = Query(default="auto"),
    quality: str = Query(default="320k"),
):
    if not keyword.strip() and not id.strip() and not mid.strip():
        return fail(400, "keyword 或 id 不能为空")
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        song = await music_play.play_song(
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
        return fail(502, "取流失败")
    if not song or not song.get("url"):
        return fail(404, "未找到可播放曲目")
    return ok(song)


@router.get("/songs/random")
async def songs_random(
    request: Request,
    src: str = Query(default=""),
):
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        song = await music_play.random_song(client, settings, src=src)
    except Exception:
        return fail(502, "随机取流失败")
    if not song or not song.get("url"):
        return fail(404, "当前没有可随机的曲目")
    return ok(song)


@router.get("/songs/{song_id}")
async def songs_by_id(
    request: Request,
    song_id: str,
    src: str = Query(default="kw"),
    source: str = Query(default="online"),
    quality: str = Query(default="320k"),
):
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        song = await music_play.play_song(
            client,
            settings,
            song_id=song_id,
            src=src,
            source=source,
            quality=quality,
        )
    except Exception:
        return fail(502, "按 ID 取流失败")
    if not song or not song.get("url"):
        return fail(404, f"曲目不存在: {song_id}")
    return ok(song)
