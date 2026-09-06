from __future__ import annotations

from typing import Any

from app.models.response import fail, ok


def to_track(
    *,
    name: str,
    artists: str,
    url: str = "",
    cover: str = "",
    duration: int | None = None,
    mv: str = "",
    track_id: str = "",
    track_type: str = "music",
    album: str = "",
) -> dict:
    track = {
        "name": name or "",
        "artists": artists or "",
        "url": (url or "").replace("https://", "http://"),
        "cover": (cover or "").replace("https://", "http://"),
        "duration": duration,
        "mv": mv or "",
    }
    if track_id:
        track["id"] = track_id
    if track_type:
        track["type"] = track_type
    if album:
        track["album"] = album
    return track


__all__ = ["fail", "ok", "to_track"]
