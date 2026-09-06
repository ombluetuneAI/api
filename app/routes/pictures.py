from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.deps import get_http
from app.services import image as image_service

router = APIRouter(prefix="/pictures/v1", tags=["pictures"])


@router.get("/random")
async def random_pic(request: Request, w: int = Query(default=0), h: int = Query(default=0)):
    image, fmt = await image_service.get_rand_pic(get_http(request), w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)


@router.get("/resize")
async def resize(
    request: Request,
    url: str = Query(default=""),
    w: int = Query(default=100),
    h: int = Query(default=100),
):
    image, fmt = await image_service.pic_resize(get_http(request), url, w, h)
    if image and fmt:
        return Response(content=image, media_type=f"image/{fmt}")
    return Response(status_code=404)
