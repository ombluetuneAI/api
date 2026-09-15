from __future__ import annotations

import os

from app.config import Settings


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


def _get_local_music_name(music_path: str, name: str) -> str:
    if not music_path or not os.path.isdir(music_path):
        return ""
    for filename in os.listdir(music_path):
        local_name = os.path.splitext(filename)[0]
        if is_name_same(name, local_name):
            return filename
    return ""


def find_local_url(settings: Settings, keyword: str) -> str | None:
    local_name = _get_local_music_name(settings.music_path, keyword)
    if local_name:
        return f"{settings.music_files_base_url}/{local_name}"
    return None
