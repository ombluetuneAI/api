from fastapi import APIRouter, Query, Request

from app.deps import get_app_settings, get_http
from app.services import music as music_service
from app.services import music_cache, local_music

router = APIRouter(tags=["music"])


@router.get("/rand_music")
async def rand_music(request: Request):
    return await music_cache.get_rand_music_from_cache(get_http(request), get_app_settings(request))


@router.get("/music")
async def music(
    request: Request,
    msg: str = Query(default=""),
    src: str = Query(default=""),
    id: str = Query(default=""),
    mid: str = Query(default=""),
):
    info = {"song": msg, "src": src, "id": id, "mid": mid}
    return local_music.get_local_music(get_app_settings(request), info)


@router.get("/api/{src}")
async def music_url(
    request: Request,
    src: str,
    id: str = Query(default=""),
    mid: str = Query(default=""),
    quality: str = Query(default="320k"),
):
    return await music_service.music_api(get_http(request), src, id, mid=mid, quality=quality)
