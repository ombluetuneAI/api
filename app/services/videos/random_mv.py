from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.services.music import play
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list


async def random_mv_url(client: httpx.AsyncClient, settings: Settings) -> str:
    rows = csv_read_list(settings.netease_playlist_hot)
    if rows:
        for _ in range(min(5, len(rows))):
            info = audio_csv_to_json(random.choice(rows))
            mv = (info.get("mv") or "").replace("https", "http")
            if mv:
                return mv
    song = await play.random_song(client, settings, src="wy")
    if song:
        return (song.get("mv") or "").replace("https", "http")
    return ""
