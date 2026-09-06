from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from app.deps import get_app_settings, get_http
from app.models.response import fail, ok
from app.services import local_music, music as music_service, music_cache, radio as radio_service
from app.services import image as image_service
from app.services import music_play
from app.services.v1 import radio as radio_v1

router = APIRouter(tags=["legacy"], deprecated=True)


# --- audio/v1 compatibility ---

audio = APIRouter(prefix="/audio/v1", deprecated=True)


@audio.get("/health")
async def audio_health():
    return ok({"status": "ok"})


@audio.get("/search")
async def audio_search(
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


@audio.get("/song/random")
async def audio_song_random(request: Request):
    client = get_http(request)
    settings = get_app_settings(request)
    song = await music_play.random_song(client, settings)
    if not song or not song.get("url"):
        return fail(404, "当前没有可随机的曲目")
    return ok(song)


@audio.get("/song")
async def audio_song_keyword(request: Request, keyword: str = Query(default="")):
    if not keyword.strip():
        return fail(400, "keyword 不能为空")
    client = get_http(request)
    settings = get_app_settings(request)
    song = await music_play.play_song(
        client, settings, keyword=keyword.strip(), source="online"
    )
    if not song:
        return fail(404, f"未找到匹配曲目: {keyword}")
    if not song.get("url"):
        return fail(502, "找到曲目但取流失败")
    return ok(song)


@audio.get("/song/{track_id}")
async def audio_song_id(request: Request, track_id: str):
    client = get_http(request)
    settings = get_app_settings(request)
    song = await music_play.play_song(
        client, settings, song_id=track_id, src="kw", source="online"
    )
    if not song:
        return fail(404, f"曲目不存在: {track_id}")
    if not song.get("url"):
        return fail(502, "取流失败")
    return ok(song)


@audio.get("/radio")
async def audio_radio(request: Request, name: str = Query(default="")):
    if not name.strip():
        return fail(400, "name 不能为空")
    client = get_http(request)
    settings = get_app_settings(request)
    try:
        track = await radio_v1.resolve_radio(client, settings, name.strip())
    except Exception:
        return fail(502, "电台上游失败")
    if not track or not track.get("url"):
        return fail(404, f"未找到匹配电台: {name}")
    return ok(track)


router.include_router(audio)


# --- music legacy ---

@router.get("/rand_music")
async def rand_music(request: Request):
    return await music_cache.get_rand_music_from_cache(
        get_http(request), get_app_settings(request)
    )


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


# --- radio legacy ---

@router.get("/rand_radio")
@router.get("/rand_fm")
async def rand_radio(request: Request):
    return await radio_service.get_rand_radio(get_http(request), get_app_settings(request))


@router.get("/favorite_radio")
@router.get("/hot_fm")
async def favorite_radio(request: Request):
    return radio_service.get_favorite_radio(get_app_settings(request))


# --- media legacy ---

@router.get("/rand_mv")
async def rand_mv(request: Request):
    mv = await music_service.get_rand_mv(get_http(request), get_app_settings(request))
    if mv:
        return RedirectResponse(url=mv, status_code=302)
    return Response(status_code=404)


@router.get("/rand_pic")
async def rand_pic(request: Request, w: int = Query(default=0), h: int = Query(default=0)):
    image, fmt = await image_service.get_rand_pic(get_http(request), w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)


@router.get("/pic_resize")
async def pic_resize(
    request: Request,
    url: str = Query(default=""),
    w: int = Query(default=100),
    h: int = Query(default=100),
):
    image, fmt = await image_service.pic_resize(get_http(request), url, w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)


# --- content legacy ---

@router.get("/dailyhot")
async def dailyhot(request: Request):
    return await music_service.get_dailyhot(get_http(request))


# --- weather legacy ---

@router.get("/weather")
async def weather(request: Request):
    from app.services import weather as weather_service

    return await weather_service.get_weather(get_http(request), get_app_settings(request))


@router.get("/qweather")
async def qweather(request: Request, url: str = Query(default="")):
    from app.services import weather as weather_service

    target = url
    if not target:
        for key in request.query_params:
            if key.startswith("http"):
                target = key
                break
    if not target:
        return {"code": 400, "msg": "missing url"}
    return await weather_service.get_qweather(get_http(request), target)


# --- proxy legacy ---

@router.get("/get_proxy")
async def get_proxy(request: Request):
    settings = get_app_settings(request)
    ip = image_service.get_random_proxy(settings.proxy_list)
    if not ip:
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ip)
