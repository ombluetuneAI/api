from fastapi import APIRouter, Query, Request

from app.deps import get_app_settings, get_http
from app.services import weather as weather_service

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def weather(request: Request):
    return await weather_service.get_weather(get_http(request), get_app_settings(request))


@router.get("/qweather")
async def qweather(request: Request, url: str = Query(default="")):
    target = url
    if not target:
        for key in request.query_params:
            if key.startswith("http"):
                target = key
                break
    if not target:
        return {"code": 400, "msg": "missing url"}
    return await weather_service.get_qweather(get_http(request), target)
