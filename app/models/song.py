from __future__ import annotations


def parse_prefixed_id(raw_id: str, default_src: str = "kw") -> tuple[str, str]:
    """Split legacy 'kw:228908' or return (default_src, raw_id)."""
    if not raw_id:
        return default_src, ""
    if ":" in raw_id:
        src, song_id = raw_id.split(":", 1)
        return src, song_id
    return default_src, raw_id


def to_song(
    data: dict,
    *,
    src: str = "",
    resolved_from: str | None = None,
) -> dict:
    """Normalize track dict to Song response shape."""
    raw_id = str(data.get("id") or "")
    parsed_src, song_id = parse_prefixed_id(raw_id, default_src=src or "kw")
    final_src = src or parsed_src

    song = {
        "id": song_id,
        "src": final_src,
        "name": data.get("name") or "",
        "artists": data.get("artists") or "",
        "album": data.get("album") or "",
        "url": (data.get("url") or "").replace("https://", "http://"),
        "cover": (data.get("cover") or data.get("pic") or "").replace("https://", "http://"),
        "duration": data.get("duration"),
        "mv": data.get("mv") or "",
    }
    if resolved_from:
        song["resolved_from"] = resolved_from
    return song
