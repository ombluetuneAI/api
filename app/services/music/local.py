"""从 local_music_index.csv 解析本地播放地址（只读）。
"""

from __future__ import annotations

from app.config import Settings
from app.utils.csv_io import csv_read_list

__all__ = ["find_local_url", "is_name_same"]

def _song_name_change(name: str) -> str:
    name = (
        name.replace(" ", "")
        .replace("/", ",")
        .replace("&", ",")
        .replace("、", ",")
        .replace("（", "(")
        .replace("）", ")")
        .replace("ive版", "ive")
    )
    if "主题曲" in name or "片尾曲" in name:
        parts = name.split("-")
        if len(parts) == 3:
            name = f"{parts[0]}-{parts[2]}"
    return name


def is_name_same(name1: str, name2: str) -> bool:
    name1 = _song_name_change(name1)
    name2 = _song_name_change(name2)
    if "-" not in name1 or "-" not in name2:
        return name1 == name2
    parts1 = name1.split("-")
    parts2 = name2.split("-")
    song1 = parts1[0]
    song2 = parts2[0]
    singer1 = parts1[1].split(",") if len(parts1) > 1 else []
    singer2 = parts2[1].split(",") if len(parts2) > 1 else []
    if song1 == song2:
        for singer in singer1:
            if singer in singer2:
                return True
    return False


def _load_index_rows(index_file: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for row in csv_read_list(index_file):
        if len(row) < 2:
            continue
        local_name, filename = row[0].strip(), row[1].strip()
        if local_name and filename:
            rows.append((local_name, filename))
    return rows


def _get_local_music_name(index_file: str, name: str) -> str:
    if not index_file or not name:
        return ""
    for local_name, filename in _load_index_rows(index_file):
        if is_name_same(name, local_name):
            return filename
    return ""


def find_local_url(settings: Settings, keyword: str) -> str | None:
    local_name = _get_local_music_name(settings.local_music_index_file, keyword)
    if local_name:
        return f"{settings.music_files_base_url}/{local_name}"
    return None
