from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.services.radio.qingting import fetch_programs
from app.utils.csv_io import csv_read_list


async def random_station(
    client: httpx.AsyncClient, settings: Settings
) -> dict | None:
    ids = csv_read_list(settings.fm_all_id)
    if not ids:
        return None
    station_id = str(random.choice(ids)[0]).strip()
    programs = await fetch_programs(client, station_id)
    if not programs:
        return None
    info = random.choice(programs)
    info["id"] = station_id
    return info
