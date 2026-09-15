from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.models.song import build_track
from app.services.radio.catalog import find_stations_by_name
from app.services.radio.qingting import fetch_programs


async def resolve_by_name(
    client: httpx.AsyncClient, settings: Settings, name: str
) -> dict | None:
    matches = find_stations_by_name(settings, name, limit=5)
    if not matches:
        return None
    for sid, sname in matches:
        programs = await fetch_programs(client, sid)
        if not programs:
            continue
        prog = random.choice(programs)
        return build_track(
            track_id=f"radio:{sid}",
            name=prog.get("name") or sname,
            artists=prog.get("artists") or sname,
            url=prog.get("url") or "",
            cover=prog.get("pic") or "",
            duration=None,
            mv="",
            track_type="radio",
        )
    return None
