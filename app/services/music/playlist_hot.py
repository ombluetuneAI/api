"""热榜 CSV：过期检测与从各平台拉取并写回。"""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import Settings
from app.logging_setup import get_logger
from app.services.music.cache import normalize_src
from app.utils.audio import UA
from app.utils.csv_io import csv_write_list

logger = get_logger(__name__)

_SRC_ATTR = {
    "kw": "kw_playlist_hot",
    "wy": "netease_playlist_hot",
    "kg": "kg_playlist_hot",
    "qq": "tx_playlist_hot",
    "tx": "tx_playlist_hot",
}

_refresh_locks: dict[str, asyncio.Lock] = {}

# 与 tests/misc.py 定时任务一致，按北京时间自然日判断是否需刷新
_CN_TZ = timezone(timedelta(hours=8))


def _today_cn() -> date:
    return datetime.now(_CN_TZ).date()


def _file_mtime_date_cn(path: str) -> date | None:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=_CN_TZ).date()
    except OSError:
        return None


def hot_csv_path(settings: Settings, src: str) -> str:
    attr = _SRC_ATTR.get(normalize_src(src))
    if not attr:
        return ""
    return getattr(settings, attr, "")


def is_hot_csv_stale(path: str) -> bool:
    """文件不存在、为空，或最后修改日不是今天（北京时间）则视为过期。"""
    if not path or not os.path.exists(path):
        return True
    try:
        if os.path.getsize(path) == 0:
            return True
    except OSError:
        return True
    file_day = _file_mtime_date_cn(path)
    if file_day is None:
        return True
    return file_day != _today_cn()


async def _fetch_netease_rows(client: httpx.AsyncClient) -> list[list[str]]:
    lrc_prefix = "http://music.163.com/api/song/lyric?id="
    r = await client.get(
        "https://music.163.com/api/playlist/detail?id=3778678&n=200",
        headers={"Referer": "https://music.163.com/", "User-Agent": UA},
        timeout=30.0,
    )
    r.raise_for_status()
    payload = r.json()
    playlist = payload.get("playlist") or payload.get("result") or {}
    tracks = playlist.get("tracks") or []
    rows: list[list[str]] = []
    for data in tracks:
        sid = str(data.get("id", ""))
        if not sid:
            continue
        artists = data.get("artists") or []
        artist = artists[0].get("name", "") if artists else ""
        album = data.get("album") or {}
        pic = album.get("picUrl", "") or ""
        name = data.get("name", "")
        lrc_url = f"{lrc_prefix}{sid}&lv=-1&kv=-1&tv=-1"
        rows.append([name, artist, sid, pic, lrc_url])
    return rows


async def _fetch_qq_rows(client: httpx.AsyncClient) -> list[list[str]]:
    date = datetime.now().strftime("%Y-%m-%d")
    top_id = 26
    inner = (
        '{"detail":{"module":"musicToplist.ToplistInfoServer","method":"GetDetail",'
        f'"param":{{"topId":{top_id},"offset":0,"num":100,"period":"{date}"}}}},'
        '"comm":{"ct":24,"cv":0}}'
    )
    url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?g_tk=5381&data={quote(inner, safe='')}"
    r = await client.get(url, headers={"User-Agent": UA}, timeout=30.0)
    r.raise_for_status()
    song_list = r.json().get("detail", {}).get("data", {}).get("songInfoList") or []
    rows: list[list[str]] = []
    for item in song_list:
        name = item.get("title", "")
        artist = "/".join(s.get("name", "") for s in item.get("singer", []) if s.get("name"))
        songmid = item.get("mid", "")
        if name and songmid:
            rows.append([name, artist, songmid])
    return rows


async def _fetch_kw_chart(client: httpx.AsyncClient, chart_id: int) -> list[list[str]]:
    url = (
        "http://kbangserver.kuwo.cn/ksong.s?from=pc&fmt=json&pn=0&rn=500"
        f"&type=bang&data=content&id={chart_id}&show_copyright_off=0&pcmp4=1"
        "&isbang=1&userid=0&httpStatus=1"
    )
    r = await client.get(url, timeout=30.0)
    r.raise_for_status()
    musiclist = r.json().get("musiclist") or []
    rows: list[list[str]] = []
    for item in musiclist:
        name = item.get("name", "")
        artist = item.get("artist", "")
        sid = str(item.get("id", ""))
        if name and sid:
            rows.append([name, artist, sid])
    return rows


async def _fetch_kw_rows(client: httpx.AsyncClient) -> list[list[str]]:
    merged: list[list[str]] = []
    seen: set[tuple[str, str, str]] = set()
    for chart_id in (16, 26):
        for row in await _fetch_kw_chart(client, chart_id):
            key = (row[0], row[1], row[2])
            if key not in seen:
                seen.add(key)
                merged.append(row)
    return merged


async def _fetch_kg_chart(client: httpx.AsyncClient, rank_id: int) -> list[list[str]]:
    url = (
        "http://mobilecdnbj.kugou.com/api/v3/rank/song?version=9108&ranktype=0&plat=0"
        f"&pagesize=1000&area_code=1&page=1&volid=35050&rankid={rank_id}&with_res_tag=0"
    )
    r = await client.get(url, timeout=30.0)
    r.raise_for_status()
    info = r.json().get("data", {}).get("info") or []
    rows: list[list[str]] = []
    for item in info:
        name = item.get("songname", "")
        artist = "/".join(
            a.get("author_name", "") for a in item.get("authors", []) if a.get("author_name")
        )
        sid = item.get("hash", "")
        if name and sid:
            rows.append([name, artist, sid])
    return rows


async def _fetch_kg_rows(client: httpx.AsyncClient) -> list[list[str]]:
    rank_ids = (8888, 49225, 49223)
    merged: list[list[str]] = []
    seen: set[tuple[str, str, str]] = set()
    for rank_id in rank_ids:
        for row in await _fetch_kg_chart(client, rank_id):
            key = (row[0], row[1], row[2])
            if key not in seen:
                seen.add(key)
                merged.append(row)
    return merged


async def _fetch_rows_for_src(client: httpx.AsyncClient, src: str) -> list[list[str]]:
    s = normalize_src(src)
    if s == "wy":
        return await _fetch_netease_rows(client)
    if s == "qq":
        return await _fetch_qq_rows(client)
    if s == "kw":
        return await _fetch_kw_rows(client)
    if s == "kg":
        return await _fetch_kg_rows(client)
    return []


def _write_hot_csv(path: str, rows: list[list[str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    csv_write_list(path, rows, "w")


async def refresh_hot_csv(
    client: httpx.AsyncClient,
    settings: Settings,
    src: str,
) -> bool:
    path = hot_csv_path(settings, src)
    if not path:
        return False
    try:
        rows = await _fetch_rows_for_src(client, src)
    except Exception:
        logger.exception("refresh hot playlist failed src=%s", src)
        return False
    if not rows:
        logger.warning("refresh hot playlist empty src=%s", src)
        return False
    _write_hot_csv(path, rows)
    logger.info("refreshed hot playlist src=%s path=%s rows=%d", src, path, len(rows))
    return True


async def ensure_hot_csv(
    client: httpx.AsyncClient,
    settings: Settings,
    src: str,
) -> None:
    path = hot_csv_path(settings, src)
    if not path:
        return
    if not is_hot_csv_stale(path):
        return

    s = normalize_src(src)
    lock = _refresh_locks.setdefault(s, asyncio.Lock())
    async with lock:
        if not is_hot_csv_stale(path):
            return
        await refresh_hot_csv(client, settings, s)


async def ensure_hot_csv_many(
    client: httpx.AsyncClient,
    settings: Settings,
    sources: list[str],
) -> None:
    unique = []
    seen: set[str] = set()
    for raw in sources:
        s = normalize_src(raw)
        if s in _SRC_ATTR and s not in seen:
            seen.add(s)
            unique.append(s)
    if not unique:
        return
    await asyncio.gather(*(ensure_hot_csv(client, settings, s) for s in unique))
