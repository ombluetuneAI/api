from __future__ import annotations

import random
import re
import time
from datetime import datetime

import httpx

from app.config import Settings
from app.logging_setup import get_logger
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list

logger = get_logger(__name__)

MUSIC_ERR_URL_RSP = {"code": 1, "msg": "未知错误"}


async def _music_url_kw(
    client: httpx.AsyncClient, name: str, artist: str, quality: str = "320k"
) -> dict:
    quality_map = {"320k": "2", "flac": "1"}
    if quality not in quality_map:
        return MUSIC_ERR_URL_RSP
    url = f"http://oiapi.net/API/Kuwo?msg={name}-{artist}&n=1&br={quality_map[quality]}"
    try:
        logger.info("request: %s", url)
        r = await client.get(url, timeout=3.0)
        raw = r.json()
        return {
            "code": 0,
            "msg": "success",
            "url": raw.get("data", {}).get("url", ""),
            "pic": raw.get("data", {}).get("picture", ""),
        }
    except Exception:
        return MUSIC_ERR_URL_RSP


async def music_url_api(
    client: httpx.AsyncClient,
    src: str,
    song_id: str,
    name: str = "",
    artist: str = "",
    quality: str = "320k",
) -> dict:
    if src == "kw":
        data = await _music_url_kw(client, name or song_id, artist, quality)
        if data.get("msg") == "success":
            return data
    return MUSIC_ERR_URL_RSP


async def _get_rand_music(
    client: httpx.AsyncClient, settings: Settings, src: str, playlist: str
) -> dict | None:
    logger.info("%s_get_rand_music", src)
    try:
        music = csv_read_list(playlist)
        if not music:
            return None
        rand_row = random.choice(music)
        info = audio_csv_to_json(rand_row)
        song_id = info.get("url", "")
        name = info.get("name", "")
        artist = info.get("artists", "")
        data = await music_url_api(client, src, song_id, name=name, artist=artist, quality="320k")
        url = (data.get("url") or "").replace("https", "http")
        pic = (data.get("pic") or "").replace("https", "http")
        if url:
            info["url"] = url
            info["pic"] = pic
            return info
    except Exception:
        logger.info("get err")
    return None


async def get_rand_music(client: httpx.AsyncClient, settings: Settings) -> dict:
    src_table = [
        ("tx", settings.tx_playlist_hot),
        ("wy", settings.netease_playlist_hot),
        ("kg", settings.kg_playlist_hot),
        ("kw", settings.kw_playlist_hot),
    ]
    random.shuffle(src_table)
    for src, playlist in src_table:
        music_info = await _get_rand_music(client, settings, src, playlist)
        if music_info:
            return {"code": 200, "data": music_info}
    return {"code": 404}


async def music_api(
    client: httpx.AsyncClient, src: str, song_id: str, mid: str = "", quality: str = "320k"
) -> dict:
    return await music_url_api(client, src, song_id, name=mid, artist="", quality=quality)


async def get_rand_mv(client: httpx.AsyncClient, settings: Settings) -> str:
    info = await _get_rand_music(client, settings, "wy", settings.netease_playlist_hot)
    if info:
        return info.get("mv", "") or ""
    return ""


def parse_hot_num(value) -> int:
    if value is None:
        return 0
    text = str(value).replace(",", "")
    nums = re.findall(r"\d+", text)
    if not nums:
        return 0
    hot = int(nums[0])
    if "万" in text and hot < 10000:
        hot *= 10000
    return hot


async def get_dailyhot(client: httpx.AsyncClient) -> dict:
    url = "https://api.qqsuu.cn/api/dm-weibohot"
    r = await client.get(url, timeout=10.0)
    r.raise_for_status()
    raw = r.json()
    news = []
    for item in raw.get("data", {}).get("list", []):
        news.append({
            "title": item.get("hotword", ""),
            "hot": parse_hot_num(item.get("hotwordnum", "")),
        })
    return {
        "code": 200,
        "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": news,
    }
