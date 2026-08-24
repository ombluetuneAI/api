from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse, Response

from app.deps import get_app_settings, get_http
from app.services import image as image_service
from app.services import music as music_service

router = APIRouter(tags=["media"])


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
