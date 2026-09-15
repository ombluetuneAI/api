from __future__ import annotations

import asyncio

import httpx

from app.logging_setup import get_logger
from app.models.song import build_track, parse_prefixed_id
from app.services.music.cache import normalize_src

logger = get_logger(__name__)

SUPPORTED_SOURCES = frozenset({"kw", "wy", "kg", "qq"})
KEYWORD_PLATFORMS = ("kw", "wy", "kg", "qq")

QUALITY_MAP = {
    "320k": "high",
    "128k": "standard",
    "flac": "lossless",
    "lossless": "lossless",
    "best": "best",
    "high": "high",
    "standard": "standard",
}


def is_valid_play_url(url: str) -> bool:
    u = (url or "").lower()
    if not u.startswith("http"):
        return False
    if any(token in u for token in ("mp3", "flac", "m4a", ".aac")):
        return True
    known_hosts = (
        "kuwo.cn",
        "music.126.net",
        "qqmusic.qq.com",
        "stream.qqmusic.qq.com",
        "kugou.com",
    )
    return any(host in u for host in known_hosts)


def map_quality(quality: str) -> str:
    return QUALITY_MAP.get((quality or "").strip().lower(), "high")


def split_keyword(keyword: str) -> tuple[str, str]:
    text = (keyword or "").strip()
    if "-" in text:
        name, artists = text.split("-", 1)
        return name.strip(), artists.strip()
    return text, ""


def resolve_ids(src: str, song_id: str = "", mid: str = "") -> tuple[str, str]:
    from app.services.music.cache import QQ_SOURCES

    src = normalize_src(src) or "kw"
    parsed_src, bare_id = parse_prefixed_id((song_id or "").strip(), src)
    final_src = normalize_src(parsed_src) if ":" in (song_id or "") else src
    if final_src in QQ_SOURCES:
        return final_src, (mid or bare_id).strip()
    return final_src, bare_id


def _parse_result_to_track(result, keyword: str = "") -> dict | None:
    if not result.ok:
        return None
    url = (result.download_url or "").strip()
    if not is_valid_play_url(url):
        return None
    platform = normalize_src(result.platform)
    name, artists = split_keyword(keyword)
    return build_track(
        track_id=f"{platform}:{result.song_id}",
        name=name,
        artists=artists,
        url=url,
        track_type="music",
    )


def _music_dl_parse(src: str, song_id: str, keyword: str, quality: str) -> dict | None:
    src = normalize_src(src)
    if src not in SUPPORTED_SOURCES:
        return None
    song_id = (song_id or "").strip()
    keyword = (keyword or "").strip()
    if not song_id and not keyword:
        return None
    try:
        from music_dl import parse
    except ImportError:
        logger.warning("music_dl not installed, skip parse for src=%s", src)
        return None

    mapped_quality = map_quality(quality)
    try:
        result = parse(src, song_id, keyword, quality=mapped_quality)
    except Exception:
        logger.exception("music_dl parse failed src=%s id=%s", src, song_id)
        return None
    return _parse_result_to_track(result, keyword)


async def resolve_via_music_dl(
    client: httpx.AsyncClient,
    src: str,
    song_id: str,
    keyword: str = "",
    quality: str = "320k",
) -> dict | None:
    del client
    return await asyncio.to_thread(_music_dl_parse, src, song_id, keyword, quality)


async def resolve_track(
    client: httpx.AsyncClient,
    *,
    src: str = "",
    song_id: str = "",
    mid: str = "",
    keyword: str = "",
    quality: str = "320k",
) -> dict | None:
    src = normalize_src(src)
    kw = (keyword or "").strip()
    final_src, resolve_id = resolve_ids(src, song_id, mid)

    if resolve_id:
        return await resolve_via_music_dl(
            client, final_src, resolve_id, kw, quality=quality
        )

    if not kw:
        return None

    platforms = [final_src] if final_src else list(KEYWORD_PLATFORMS)
    for platform in platforms:
        if platform not in SUPPORTED_SOURCES:
            continue
        track = await resolve_via_music_dl(
            client, platform, "", kw, quality=quality
        )
        if track:
            return track
    return None
