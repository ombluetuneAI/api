from fastapi import APIRouter, Request

from app.deps import get_app_settings, get_http
from app.services import radio as radio_service

router = APIRouter(tags=["radio"])


@router.get("/rand_radio")
@router.get("/rand_fm")
async def rand_radio(request: Request):
    return await radio_service.get_rand_radio(get_http(request), get_app_settings(request))


@router.get("/favorite_radio")
@router.get("/hot_fm")
async def favorite_radio(request: Request):
    return radio_service.get_favorite_radio(get_app_settings(request))
