from __future__ import annotations

import random
from datetime import datetime, timedelta

import httpx

from app.config import Settings
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list


async def fm_get_cur_id_info(client: httpx.AsyncClient, station_id: str) -> list[dict]:
    r = await client.get(f"https://webapi.qingting.fm/api/pc/radio/{station_id}", timeout=3.0)
    data = r.json()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    if not data.get("album"):
        return []
    pic = data["album"]["cover"]
    artists = data["album"]["title"]
    today = datetime.now().weekday()
    today = (today + 1) if (today + 1) <= 6 else 7
    d_data = data.get("pList", {}).get(str(today), [])
    music_infos = []
    for item in d_data:
        name = item["title"]
        start_time = item["start_time"].replace(":", "")
        end_time = item["end_time"].replace(":", "")
        url = (
            f"http://lcache.qtfm.cn/cache/{yesterday}/{station_id}/"
            f"{station_id}_{yesterday}_{start_time}_{end_time}_24_0.aac"
        )
        music_infos.append({
            "name": name,
            "artists": artists,
            "url": url,
            "pic": pic,
        })
    return music_infos


async def get_rand_radio(client: httpx.AsyncClient, settings: Settings) -> dict:
    ids = csv_read_list(settings.fm_all_id)
    if not ids:
        return {"code": 404}
    music_infos = await fm_get_cur_id_info(client, random.choice(ids)[0])
    if not music_infos:
        return {"code": 404}
    music_info = random.choice(music_infos)
    return {"code": 200, "data": music_info}


def get_favorite_radio(settings: Settings) -> dict:
    music_infos = csv_read_list(settings.fm_playlist_hot)
    if not music_infos:
        return {"code": 404}
    music_info = audio_csv_to_json(random.choice(music_infos))
    return {"code": 200, "data": music_info}
