from __future__ import annotations

import asyncio
import time

from app.config import Settings
from app.logging_setup import get_logger
from app.services.music import get_rand_music

logger = get_logger(__name__)

_cache_music: dict = {}
_cache_time: int = 0
_bg_tasks: set[asyncio.Task] = set()


async def _refresh_cache(client, settings: Settings) -> None:
    global _cache_music, _cache_time
    try:
        result = await get_rand_music(client, settings)
        _cache_music = result
        _cache_time = int(time.time())
    except Exception:
        logger.exception("refresh music cache failed")


def schedule_music_cache_refresh(client, settings: Settings) -> None:
    task = asyncio.create_task(_refresh_cache(client, settings))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


async def get_rand_music_from_cache(client, settings: Settings) -> dict:
    global _cache_music, _cache_time
    music: dict = {}
    if time.time() - _cache_time < 3600 and _cache_music:
        music = dict(_cache_music)
    if not music:
        music = await get_rand_music(client, settings)
    _cache_music = {}
    schedule_music_cache_refresh(client, settings)
    logger.info(music)
    return music
