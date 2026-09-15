from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.utils.csv_io import csv_read_list


def load_stations(settings: Settings) -> list[tuple[str, str]]:
    stations: list[tuple[str, str]] = []
    for path in (settings.fm_all_id, settings.fm_hot_id):
        for row in csv_read_list(path):
            if not row:
                continue
            sid = str(row[0]).strip()
            name = str(row[1]).strip() if len(row) > 1 else sid
            if sid:
                stations.append((sid, name))

    sources = Path(settings.fm_sources_dir)
    if sources.is_dir():
        for csv_file in sources.glob("*.csv"):
            for row in csv_read_list(str(csv_file)):
                if not row:
                    continue
                sid = str(row[0]).strip()
                name = str(row[1]).strip() if len(row) > 1 else sid
                if sid:
                    stations.append((sid, name))

    seen = set()
    uniq = []
    for sid, name in stations:
        if sid in seen:
            continue
        seen.add(sid)
        uniq.append((sid, name))
    return uniq


def find_stations_by_name(settings: Settings, name: str, limit: int = 10) -> list[tuple[str, str]]:
    stations = load_stations(settings)
    if not name:
        return stations[:limit]
    key = name.strip().lower()
    exact = [(s, n) for s, n in stations if n.lower() == key]
    if exact:
        return exact[:limit]
    partial = [(s, n) for s, n in stations if key in n.lower()]
    return partial[:limit]
