from __future__ import annotations


def parse_prefixed_id(raw_id: str, default_src: str = "kw") -> tuple[str, str]:
    """Split internal 'kw:228908' or return (default_src, raw_id)."""
    if not raw_id:
        return default_src, ""
    if ":" in raw_id:
        src, song_id = raw_id.split(":", 1)
        return src, song_id
    return default_src, raw_id


def build_track(
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


def to_song(
    data: dict,
    *,
    src: str = "",
    resolved_from: str | None = None,
) -> dict:
    """Normalize track dict to unified media response shape."""
    raw_id = str(data.get("id") or "")
    parsed_src, song_id = parse_prefixed_id(raw_id, default_src=src or "kw")
    final_src = src or parsed_src

    return {
        "id": song_id,
        "src": final_src,
        "name": data.get("name") or "",
        "artists": data.get("artists") or "",
        "album": data.get("album") or "",
        "url": (data.get("url") or "").replace("https://", "http://"),
        "cover": (data.get("cover") or data.get("pic") or "").replace("https://", "http://"),
        "duration": data.get("duration"),
        "mv": data.get("mv") or "",
        "category": data.get("category") or "",
        "region": data.get("region") or "",
        "resolved_from": resolved_from or data.get("resolved_from") or "",
    }
