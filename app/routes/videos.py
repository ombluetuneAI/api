from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from app.deps import get_app_settings, get_http
from app.services import music as music_service

router = APIRouter(prefix="/videos/v1", tags=["videos"])


@router.get("/random")
async def random_mv(request: Request):
    mv = await music_service.get_rand_mv(get_http(request), get_app_settings(request))
    if mv:
        return RedirectResponse(url=mv, status_code=302)
    return Response(status_code=404)
