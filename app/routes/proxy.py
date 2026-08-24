from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.deps import get_app_settings
from app.services import image as image_service

router = APIRouter(tags=["proxy"])


@router.get("/get_proxy")
async def get_proxy(request: Request):
    settings = get_app_settings(request)
    ip = image_service.get_random_proxy(settings.proxy_list)
    if not ip:
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse(ip)
