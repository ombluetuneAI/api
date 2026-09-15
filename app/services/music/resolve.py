from __future__ import annotations

import asyncio
import random
from typing import Callable

import httpx

from app.constants import DEFAULT_UA
from app.logging_setup import get_logger
from app.models.song import build_track, parse_prefixed_id
from app.services.music import cache, kuwo
from app.services.music.local import is_name_same

logger = get_logger(__name__)

SUPPORTED_SOURCES = frozenset({"kw", "wy", "kg", "qq"})

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
    src = cache.normalize_src(src) or "kw"
    parsed_src, bare_id = parse_prefixed_id((song_id or "").strip(), src)
    final_src = cache.normalize_src(parsed_src) if ":" in (song_id or "") else src
    if final_src in cache.QQ_SOURCES:
        return final_src, (mid or bare_id).strip()
    return final_src, bare_id


def _music_dl_resolve(src: str, song_id: str, keyword: str, quality: str) -> dict | None:
    if not song_id or src not in SUPPORTED_SOURCES:
        return None
    try:
        from music_dl import parse
    except ImportError:
        logger.warning("music_dl not installed, skip id resolve for src=%s", src)
        return None

    mapped_quality = map_quality(quality)
    try:
        result = parse(src, song_id, keyword, quality=mapped_quality)
    except Exception:
        logger.exception("music_dl failed src=%s id=%s", src, song_id)
        return None

    if not result.ok:
        return None

    url = (result.download_url or "").strip()
    if not is_valid_play_url(url):
        logger.info("music_dl invalid url src=%s id=%s url=%s", src, song_id, url[:120])
        return None

    name, artists = split_keyword(keyword)
    return build_track(
        track_id=f"{src}:{song_id}",
        name=name,
        artists=artists,
        url=url,
        track_type="music",
    )


async def resolve_via_music_dl(
    client: httpx.AsyncClient,
    src: str,
    song_id: str,
    keyword: str = "",
    quality: str = "320k",
) -> dict | None:
    del client
    return await asyncio.to_thread(_music_dl_resolve, src, song_id, keyword, quality)


async def resolve_via_oiapi_name(
    client: httpx.AsyncClient,
    keyword: str,
    *,
    src: str = "kw",
) -> dict | None:
    name = (keyword or "").strip()
    if not name:
        return None

    api = f"https://oiapi.net/API/Kuwo?msg={name}&n=1&type=json&br=1"
    try:
        logger.info("oiapi name resolve: %s", api)
        r = await client.get(api, headers={"User-Agent": DEFAULT_UA}, timeout=10.0)
        data = (r.json() or {}).get("data") or {}
        song = data.get("song") or ""
        singer = data.get("singer") or ""
        got = f"{song}-{singer}" if singer else song
        if not is_name_same(name, got):
            logger.info("oiapi name mismatch expect=%s got=%s", name, got)
            return None
        url = (data.get("url") or "").strip()
        if not is_valid_play_url(url):
            return None
        kid = str(data.get("id") or "")
        return build_track(
            track_id=f"{src}:{kid}" if kid else "",
            name=song or split_keyword(name)[0],
            artists=singer or split_keyword(name)[1],
            url=url,
            cover=(data.get("picture") or "").replace("https://", "http://"),
            track_type="music",
            album=data.get("album") or "",
        )
    except Exception:
        logger.exception("oiapi name resolve failed keyword=%s", name)
        return None


async def _try_resolvers(
    resolvers: list[Callable],
) -> dict | None:
    shuffled = list(resolvers)
    random.shuffle(shuffled)
    for resolver in shuffled:
        try:
            track = await resolver()
            if track and track.get("url") and is_valid_play_url(track["url"]):
                return track
        except Exception:
            logger.exception("resolver failed: %s", getattr(resolver, "__name__", resolver))
    return None


async def resolve_track(
    client: httpx.AsyncClient,
    *,
    src: str = "",
    song_id: str = "",
    mid: str = "",
    keyword: str = "",
    quality: str = "320k",
) -> dict | None:
    src = cache.normalize_src(src)
    kw = (keyword or "").strip()
    final_src, resolve_id = resolve_ids(src, song_id, mid)

    resolvers: list[Callable] = []

    if resolve_id:
        resolvers.append(
            lambda s=final_src, sid=resolve_id: resolve_via_music_dl(
                client, s, sid, kw, quality=quality
            )
        )

    if final_src in ("", "kw") and resolve_id:
        resolvers.append(
            lambda sid=resolve_id: kuwo.resolve_by_id(
                client, sid if sid.startswith("kw:") else f"kw:{sid}"
            )
        )

    if final_src in ("", "kw") and kw:
        resolvers.append(lambda: kuwo.search_and_resolve(client, kw))

    if kw:
        resolvers.append(
            lambda s=final_src or "kw": resolve_via_oiapi_name(client, kw, src=s)
        )

    return await _try_resolvers(resolvers)
