from __future__ import annotations

from app.models.song import to_song


def to_station(
    data: dict,
    *,
    station_id: str = "",
    category: str = "",
    region: str = "",
) -> dict:
    """与 Song 相同的统一媒体字段；电台固定 src=radio。"""
    raw_id = station_id or str(data.get("id") or "")
    if raw_id.startswith("radio:"):
        raw_id = raw_id.removeprefix("radio:")

    payload = {
        "id": raw_id,
        "name": data.get("name") or "",
        "artists": "",
        "album": "",
        "url": data.get("url") or "",
        "cover": data.get("cover") or data.get("pic") or "",
        "duration": None,
        "mv": "",
        "category": category or data.get("category") or "",
        "region": region or data.get("region") or "",
        "resolved_from": "",
    }
    return to_song(payload, src="radio")
