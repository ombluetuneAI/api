from __future__ import annotations

import random

from app.config import Settings
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list


def favorite_station(settings: Settings) -> dict | None:
    music_infos = csv_read_list(settings.fm_playlist_hot)
    if not music_infos:
        return None
    return audio_csv_to_json(random.choice(music_infos))
