from fastapi import APIRouter, Request

from app.deps import get_http
from app.services import music as music_service

router = APIRouter(prefix="/content/v1", tags=["content"])


@router.get("/dailyhot")
async def dailyhot(request: Request):
    return await music_service.get_dailyhot(get_http(request))
