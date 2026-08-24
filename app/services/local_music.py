from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import httpx

from app.config import Settings
from app.logging_setup import get_logger
from app.utils.audio import audio_csv_to_json
from app.utils.csv_io import csv_read_list, csv_write_list

logger = get_logger(__name__)

MUSIC_ERR_URL_RSP = {"code": 1, "msg": "未知错误"}


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


def save_song_requests(settings: Settings, info: dict) -> None:
    line = [info["song"], info["src"], info["id"], info["mid"], ""]
    rows = csv_read_list(settings.song_req_cache_file)
    if not any(line[0] == row[0] for row in rows):
        rows.append(line)
        csv_write_list(settings.song_req_cache_file, rows, "w")


def get_local_music(settings: Settings, info: dict) -> dict:
    logger.info("find music %s", info["song"])
    save_song_requests(settings, info)
    data = dict(MUSIC_ERR_URL_RSP)
    local_name = _get_local_music_name(settings.music_path, info["song"])
    if local_name:
        data = {
            "code": 0,
            "msg": "success",
            "music_url": f"{settings.music_files_base_url}/{local_name}",
        }
    logger.info("rsp %s", data)
    return data
