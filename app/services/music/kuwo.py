from __future__ import annotations

import ast
import json
import random
import re

import httpx

from app.config import Settings
from app.constants import DEFAULT_UA
from app.logging_setup import get_logger
from app.models.song import build_track
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list

logger = get_logger(__name__)


def _parse_kuwo_rid(musicrid: str) -> str:
    if not musicrid:
        return ""
    m = re.search(r"(\d+)", str(musicrid))
    return m.group(1) if m else str(musicrid)


def _parse_duration(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if ":" in text:
        parts = text.split(":")
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            return None
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _loads_maybe_python_dict(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return ast.literal_eval(text)


async def search_kuwo(
    client: httpx.AsyncClient, keyword: str, limit: int = 10
) -> list[dict]:
    if not keyword:
        return []
    url = "http://search.kuwo.cn/r.s"
    params = {
        "all": keyword,
        "ft": "music",
        "client": "kt",
        "pn": 0,
        "rn": max(1, min(limit, 50)),
        "rformat": "json",
        "encoding": "utf8",
    }
    r = await client.get(url, params=params, headers={"User-Agent": DEFAULT_UA}, timeout=8.0)
    raw = _loads_maybe_python_dict(r.text)
    items = []
    for row in raw.get("abslist") or []:
        rid = _parse_kuwo_rid(row.get("MUSICRID") or row.get("DC_TARGETID") or "")
        if not rid:
            continue
        name = (row.get("SONGNAME") or row.get("NAME") or "").replace("&nbsp;", " ")
        artists = (row.get("ARTIST") or "").replace("&nbsp;", " ")
        items.append(
            build_track(
                track_id=f"kw:{rid}",
                name=name,
                artists=artists,
                url="",
                cover="",
                duration=_parse_duration(row.get("DURATION")),
                mv="",
                track_type="music",
                album=row.get("ALBUM") or "",
            )
        )
    return items


async def _fetch_kuwo_info(client: httpx.AsyncClient, rid: str) -> dict:
    if not rid:
        return {}
    url = f"http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}"
    try:
        r = await client.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=5.0)
        data = (r.json() or {}).get("data") or {}
        info = data.get("songinfo") or data
        return {
            "name": info.get("songName") or info.get("name") or "",
            "artists": info.get("artist") or info.get("artistName") or "",
            "cover": info.get("pic") or info.get("pic120") or info.get("albumpic") or "",
            "duration": _parse_duration(info.get("duration") or info.get("songTimeMinutes")),
            "album": info.get("album") or "",
        }
    except Exception:
        logger.exception("kuwo info failed rid=%s", rid)
        return {}


async def resolve_kuwo_play(
    client: httpx.AsyncClient,
    *,
    rid: str = "",
    name: str = "",
    artists: str = "",
) -> dict | None:
    meta = {}
    if rid and (not name or not artists):
        meta = await _fetch_kuwo_info(client, rid)
        name = name or meta.get("name", "")
        artists = artists or meta.get("artists", "")

    query_name = name or rid
    query_artist = artists or ""
    oiapi = f"http://oiapi.net/API/Kuwo?msg={query_name}-{query_artist}&n=1&br=2"
    try:
        logger.info("kuwo oiapi: %s", oiapi)
        r = await client.get(oiapi, headers={"User-Agent": DEFAULT_UA}, timeout=5.0)
        raw = r.json()
        data = raw.get("data") or {}
        play_url = data.get("url") or ""
        if play_url:
            kid = str(data.get("id") or rid or "")
            return build_track(
                track_id=f"kw:{kid}" if kid else "",
                name=data.get("song") or name or "",
                artists=data.get("singer") or artists or "",
                url=play_url,
                cover=data.get("picture") or meta.get("cover") or "",
                duration=_parse_duration(data.get("time")) or meta.get("duration"),
                mv="",
                track_type="music",
                album=data.get("album") or meta.get("album") or "",
            )
    except Exception:
        logger.exception("kuwo oiapi failed")

    if rid:
        anti = (
            f"https://antiserver.kuwo.cn/anti.s"
            f"?type=convert_url3&rid={rid}&format=mp3&response=url&br=320kmp3"
        )
        try:
            logger.info("kuwo anti: %s", anti)
            r = await client.get(
                anti,
                headers={"User-Agent": DEFAULT_UA, "Referer": "https://www.kuwo.cn/"},
                timeout=5.0,
            )
            raw = r.json()
            play_url = raw.get("url") or ""
            if play_url:
                return build_track(
                    track_id=f"kw:{rid}",
                    name=name or "",
                    artists=artists or "",
                    url=play_url,
                    cover=meta.get("cover") or "",
                    duration=meta.get("duration"),
                    mv="",
                    track_type="music",
                    album=meta.get("album") or "",
                )
        except Exception:
            logger.exception("kuwo anti failed")
    return None


async def search_and_resolve(
    client: httpx.AsyncClient, keyword: str, *, attempts: int = 5
) -> dict | None:
    items = await search_kuwo(client, keyword, limit=max(attempts, 5))
    if not items:
        return None
    for item in items[:attempts]:
        rid = (item.get("id") or "").removeprefix("kw:")
        track = await resolve_kuwo_play(
            client,
            rid=rid,
            name=item.get("name", ""),
            artists=item.get("artists", ""),
        )
        if track and track.get("url"):
            if not track.get("name"):
                track["name"] = item.get("name", "")
            if not track.get("artists"):
                track["artists"] = item.get("artists", "")
            if track.get("duration") is None:
                track["duration"] = item.get("duration")
            return track
    return None


async def resolve_by_id(client: httpx.AsyncClient, track_id: str) -> dict | None:
    if not track_id:
        return None
    if track_id.startswith("kw:"):
        rid = track_id.removeprefix("kw:")
        return await resolve_kuwo_play(client, rid=rid)
    if track_id.isdigit():
        return await resolve_kuwo_play(client, rid=track_id)
    return None


async def random_track(client: httpx.AsyncClient, settings: Settings) -> dict | None:
    playlists = [
        ("kw", settings.kw_playlist_hot),
        ("tx", settings.tx_playlist_hot),
        ("kg", settings.kg_playlist_hot),
        ("wy", settings.netease_playlist_hot),
    ]
    random.shuffle(playlists)
    for src, path in playlists:
        rows = csv_read_list(path)
        if not rows:
            continue
        for _ in range(min(5, len(rows))):
            info = audio_csv_to_json(random.choice(rows))
            name = info.get("name", "")
            artists = info.get("artists", "")
            song_id = info.get("url", "")
            if src == "kw":
                track = await resolve_kuwo_play(
                    client, rid=str(song_id), name=name, artists=artists
                )
            else:
                track = await resolve_kuwo_play(client, name=name, artists=artists)
            if track and track.get("url"):
                if not track.get("name"):
                    track["name"] = name
                if not track.get("artists"):
                    track["artists"] = artists
                return track
    return None
