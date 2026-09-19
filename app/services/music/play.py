from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.models.song import parse_prefixed_id, to_song
from app.services.music import local
from app.services.music import music_dl_api
from app.services.music.cache import normalize_src, save_song_request
from app.services.music.playlist_hot import ensure_hot_csv, ensure_hot_csv_many
from app.services.music.resolve import resolve_track
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list

PLAYLIST_SOURCES = {
    "kw": "kw_playlist_hot",
    "wy": "netease_playlist_hot",
    "kg": "kg_playlist_hot",
    "tx": "tx_playlist_hot",
    "qq": "tx_playlist_hot",
}

def normalize_song_keyword(keyword: str) -> str:
    """统一歌名/keyword，便于本地文件名与 CSV（| -> @，/ -> ,）。"""
    s = (keyword or "").strip()
    s = s.replace("|", "@")
    s = s.replace("/", ",")
    return s


def _playlist_path(settings: Settings, src: str) -> str:
    attr = PLAYLIST_SOURCES.get(normalize_src(src))
    if not attr:
        return ""
    return getattr(settings, attr, "")


def _resolve_src_list(src: str) -> list[str]:
    if not src:
        return ["kw", "wy", "kg", "qq"]
    return [normalize_src(src)]


def _list_src_label(src: str) -> str:
    if not (src or "").strip():
        return "mixed"
    return normalize_src(src)


async def _playlist_rows(
    client: httpx.AsyncClient,
    settings: Settings,
    src: str,
) -> list[list[str]]:
    s = normalize_src(src)
    await ensure_hot_csv(client, settings, s)
    path = _playlist_path(settings, s)
    if not path:
        return []
    return csv_read_list(path)


async def search_songs(
    client: httpx.AsyncClient, keyword: str, limit: int = 10, *, src: str = ""
) -> dict:
    items = await music_dl_api.search_songs(client, keyword, limit=limit, src=src)
    return {
        "list": items,
        "total": len(items),
        "src": _list_src_label(src),
    }


async def get_playlists(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    src: str = "",
    limit: int = 20,
    resolve: bool = False,
) -> dict:
    limit = max(1, min(limit, 50))
    sources = _resolve_src_list(src)
    await ensure_hot_csv_many(client, settings, sources)
    rows_pool: list[tuple[str, list]] = []
    for s in sources:
        rows = await _playlist_rows(client, settings, s)
        if rows:
            rows_pool.append((normalize_src(s), rows))

    if not rows_pool:
        return {"list": [], "total": 0, "src": _list_src_label(src)}

    picked: list[tuple[str, dict]] = []
    attempts = 0
    while len(picked) < limit and attempts < limit * 10:
        attempts += 1
        s, rows = random.choice(rows_pool)
        info = audio_csv_to_json(random.choice(rows))
        song = to_song(
            {
                "id": info.get("url", ""),
                "name": info.get("name", ""),
                "artists": info.get("artists", ""),
                "cover": info.get("pic", ""),
                "url": "",
            },
            src=s,
        )
        if resolve and song["id"]:
            track = await resolve_track(
                client,
                src=s,
                song_id=song["id"],
                keyword=f"{song['name']}-{song['artists']}".strip("-"),
            )
            if track:
                song = to_song(track, src=s)
        picked.append((s, song))

    return {
        "list": [s for _, s in picked[:limit]],
        "total": len(picked[:limit]),
        "src": _list_src_label(src),
    }


async def play_song(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    keyword: str = "",
    song_id: str = "",
    src: str = "",
    mid: str = "",
    source: str = "auto",
    quality: str = "320k",
) -> dict | None:
    src = normalize_src(src)
    unified_id = song_id.strip()
    if src in {"qq"} and not unified_id and mid:
        unified_id = mid.strip()

    kw = normalize_song_keyword(keyword)
    if not kw and not unified_id:
        return None

    local_url = local.find_local_url(settings, kw) if kw else None
    if kw and not local_url:
        save_song_request(
            settings,
            song=kw,
            src=src,
            id=song_id.strip(),
            mid=mid.strip(),
        )

    if source == "local":
        modes = ["local"]
    elif source == "online":
        modes = ["online"]
    else:
        modes = ["local", "online"]

    for mode in modes:
        if mode == "local" and local_url:
            return to_song(
                {
                    "id": unified_id,
                    "name": kw.split("-")[0] if "-" in kw else kw,
                    "artists": kw.split("-", 1)[1] if "-" in kw else "",
                    "url": local_url,
                },
                src=src or "kw",
                resolved_from="local",
            )
        if mode == "online":
            track = await resolve_track(
                client,
                src=src,
                song_id=unified_id,
                mid=mid.strip(),
                keyword=kw,
                quality=quality,
            )
            if track and track.get("url"):
                parsed_src, _ = parse_prefixed_id(str(track.get("id", "")), src or "kw")
                return to_song(track, src=src or parsed_src, resolved_from="online")
    return None


async def random_song(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    src: str = "",
) -> dict | None:
    if src:
        rows = await _playlist_rows(client, settings, src)
        if rows:
            for _ in range(min(5, len(rows))):
                info = audio_csv_to_json(random.choice(rows))
                s = normalize_src(src)
                track = await resolve_track(
                    client,
                    src=s,
                    song_id=str(info.get("url", "")),
                    keyword=normalize_song_keyword(
                        f"{info.get('name', '')}-{info.get('artists', '')}".strip("-")
                    ),
                )
                if track and track.get("url"):
                    return to_song(track, src=s)
    sources = ["kw", "wy", "kg", "qq"] if not src else [normalize_src(src)]
    random.shuffle(sources)
    await ensure_hot_csv_many(client, settings, sources)
    for s in sources:
        rows = await _playlist_rows(client, settings, s)
        if not rows:
            continue
        for _ in range(min(5, len(rows))):
            info = audio_csv_to_json(random.choice(rows))
            track = await resolve_track(
                client,
                src=s,
                song_id=str(info.get("url", "")),
                keyword=normalize_song_keyword(
                    f"{info.get('name', '')}-{info.get('artists', '')}".strip("-")
                ),
            )
            if track and track.get("url"):
                return to_song(track, src=s)
    return None
