from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.logging_setup import get_logger
from app.models.song import to_song
from app.services.music.cache import normalize_src

if TYPE_CHECKING:
    from music_dl.search_meta import UnifiedSongMeta

logger = get_logger(__name__)

PLATFORMS = ("kw", "wy", "kg", "qq")


def meta_to_song(meta: UnifiedSongMeta) -> dict:
    duration = meta.duration_s if meta.duration_s else None
    return to_song(
        {
            "id": meta.song_id,
            "name": meta.title,
            "artists": meta.artists,
            "album": meta.album,
            "cover": meta.cover_url,
            "duration": duration,
            "url": "",
        },
        src=normalize_src(meta.platform),
    )


def _search_platform(platform: str, keyword: str, limit: int) -> list:
    try:
        from music_dl import search
    except ImportError:
        logger.warning("music_dl not installed")
        return []
    try:
        return search(platform, keyword, limit=limit)
    except Exception:
        logger.exception("music_dl search failed platform=%s", platform)
        return []


def search_all(keyword: str, limit: int = 10, src: str = "") -> list:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    limit = max(1, min(limit, 50))
    src = normalize_src(src)
    platforms = [src] if src else list(PLATFORMS)
    if len(platforms) == 1:
        return _search_platform(platforms[0], keyword, limit)[:limit]

    per = max(1, (limit + len(platforms) - 1) // len(platforms))
    batches = [_search_platform(p, keyword, per) for p in platforms]
    merged: list = []
    for i in range(per):
        for batch in batches:
            if i < len(batch) and len(merged) < limit:
                merged.append(batch[i])
    return merged[:limit]


async def search_songs(
    _client,
    keyword: str,
    limit: int = 10,
    *,
    src: str = "",
) -> list[dict]:
    metas = await asyncio.to_thread(search_all, keyword, limit, src)
    return [meta_to_song(m) for m in metas]


async def search_songs_async(keyword: str, limit: int = 10, *, src: str = "") -> list[dict]:
    return await search_songs(None, keyword, limit, src=src)
