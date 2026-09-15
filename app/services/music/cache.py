from __future__ import annotations

from app.config import Settings
from app.logging_setup import get_logger
from app.utils.csv_io import csv_read_list, csv_write_list

logger = get_logger(__name__)

QQ_SOURCES = frozenset({"qq", "tx"})


def normalize_src(src: str) -> str:
    s = (src or "").strip().lower()
    if s == "tx":
        return "qq"
    return s


def split_ids_for_cache(src: str, unified_id: str = "", legacy_mid: str = "") -> tuple[str, str]:
    """Map API id to CSV (id_col, mid_col) for dl_music compatibility."""
    src = normalize_src(src)
    uid = (unified_id or "").strip()
    mid = (legacy_mid or "").strip()

    if src in QQ_SOURCES:
        if mid:
            return uid, mid
        return "", uid or mid
    return uid or mid, ""


def save_song_request(
    settings: Settings,
    *,
    song: str,
    src: str = "",
    id: str = "",
    mid: str = "",
) -> None:
    if not song.strip():
        return
    src = normalize_src(src)
    csv_id, csv_mid = split_ids_for_cache(src, id, mid)
    line = [song.strip(), src, csv_id, csv_mid, ""]
    rows = csv_read_list(settings.song_req_cache_file)
    if not any(line[0] == row[0] for row in rows):
        rows.append(line)
        csv_write_list(settings.song_req_cache_file, rows, "w")
        logger.info("cached song request %s", line)
