from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.models.song import parse_prefixed_id, to_song
from app.services import local_music
from app.services.cache_writer import normalize_src, save_song_request
from app.services.v1 import kuwo
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list

PLAYLIST_SOURCES = {
    "kw": "kw_playlist_hot",
    "wy": "netease_playlist_hot",
    "kg": "kg_playlist_hot",
    "tx": "tx_playlist_hot",
    "qq": "tx_playlist_hot",
}


def _playlist_path(settings: Settings, src: str) -> str:
    attr = PLAYLIST_SOURCES.get(normalize_src(src))
    if not attr:
        return ""
    return getattr(settings, attr, "")


def _resolve_src_list(src: str) -> list[str]:
    if not src:
        return ["kw", "wy", "kg", "qq"]
    return [normalize_src(src)]


async def search_songs(
    client: httpx.AsyncClient, keyword: str, limit: int = 10
) -> list[dict]:
    items = await kuwo.search_kuwo(client, keyword, limit=limit)
    return [to_song(item, src="kw") for item in items]


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
    rows_pool: list[tuple[str, list]] = []
    for s in sources:
        path = _playlist_path(settings, s)
        if not path:
            continue
        rows = csv_read_list(path)
        if rows:
            rows_pool.append((normalize_src(s), rows))

    if not rows_pool:
        return {"list": [], "total": 0, "src": "mixed" if not src else normalize_src(src)}

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
        if resolve and s == "kw" and song["id"]:
            track = await kuwo.resolve_kuwo_play(
                client,
                rid=song["id"],
                name=song["name"],
                artists=song["artists"],
            )
            if track:
                song = to_song(track, src="kw")
        picked.append((s, song))

    return {
        "list": [s for _, s in picked[:limit]],
        "total": len(picked[:limit]),
        "src": "mixed" if not src else normalize_src(src),
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

    kw = keyword.strip()
    if not kw and not unified_id:
        return None

    if kw:
        save_song_request(
            settings,
            song=kw,
            src=src,
            id=song_id.strip(),
            mid=mid.strip(),
        )

    modes = []
    if source == "local":
        modes = ["local"]
    elif source == "online":
        modes = ["online"]
    else:
        modes = ["local", "online"]

    for mode in modes:
        if mode == "local" and kw:
            url = local_music.find_local_url(settings, kw)
            if url:
                return to_song(
                    {
                        "id": unified_id,
                        "name": kw.split("-")[0] if "-" in kw else kw,
                        "artists": kw.split("-", 1)[1] if "-" in kw else "",
                        "url": url,
                    },
                    src=src or "kw",
                    resolved_from="local",
                )
        if mode == "online":
            track = None
            if unified_id and (src in ("", "kw") or not src):
                track = await kuwo.resolve_by_id(client, unified_id)
            elif kw and (src in ("", "kw") or not src):
                track = await kuwo.search_and_resolve(client, kw)
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
        path = _playlist_path(settings, src)
        if path:
            rows = csv_read_list(path)
            if rows:
                for _ in range(min(5, len(rows))):
                    info = audio_csv_to_json(random.choice(rows))
                    s = normalize_src(src)
                    if s == "kw":
                        track = await kuwo.resolve_kuwo_play(
                            client,
                            rid=str(info.get("url", "")),
                            name=info.get("name", ""),
                            artists=info.get("artists", ""),
                        )
                    else:
                        track = await kuwo.resolve_kuwo_play(
                            client,
                            name=info.get("name", ""),
                            artists=info.get("artists", ""),
                        )
                    if track and track.get("url"):
                        return to_song(track, src=s)
    track = await kuwo.random_track(client, settings)
    if track and track.get("url"):
        parsed_src, _ = parse_prefixed_id(track.get("id", ""), "kw")
        return to_song(track, src=parsed_src)
    return None
