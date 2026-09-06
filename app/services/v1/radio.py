from __future__ import annotations

import random

import httpx

from app.config import Settings
from app.services.radio import fm_get_cur_id_info
from app.services.v1.models import to_track
from app.utils.csv_io import csv_read_list


def _load_stations(settings: Settings) -> list[tuple[str, str]]:
    """Return list of (station_id, station_name)."""
    stations: list[tuple[str, str]] = []
    for path in (settings.fm_all_id, settings.fm_hot_id):
        for row in csv_read_list(path):
            if not row:
                continue
            sid = str(row[0]).strip()
            name = str(row[1]).strip() if len(row) > 1 else sid
            if sid:
                stations.append((sid, name))
    # also scan source category files for richer names
    from pathlib import Path

    sources = Path("data/fm/sources")
    if sources.is_dir():
        for csv_file in sources.glob("*.csv"):
            for row in csv_read_list(str(csv_file)):
                if not row:
                    continue
                sid = str(row[0]).strip()
                name = str(row[1]).strip() if len(row) > 1 else sid
                if sid:
                    stations.append((sid, name))
    # dedupe by id
    seen = set()
    uniq = []
    for sid, name in stations:
        if sid in seen:
            continue
        seen.add(sid)
        uniq.append((sid, name))
    return uniq


def find_stations_by_name(settings: Settings, name: str, limit: int = 10) -> list[tuple[str, str]]:
    stations = _load_stations(settings)
    if not name:
        return stations[:limit]
    key = name.strip().lower()
    exact = [(s, n) for s, n in stations if n.lower() == key]
    if exact:
        return exact[:limit]
    partial = [(s, n) for s, n in stations if key in n.lower()]
    return partial[:limit]


async def resolve_radio(
    client: httpx.AsyncClient, settings: Settings, name: str
) -> dict | None:
    matches = find_stations_by_name(settings, name, limit=5)
    if not matches:
        return None
    for sid, sname in matches:
        programs = await fm_get_cur_id_info(client, sid)
        if not programs:
            continue
        prog = random.choice(programs)
        return to_track(
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
