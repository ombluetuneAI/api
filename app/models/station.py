from __future__ import annotations


def to_station(
    data: dict,
    *,
    station_id: str = "",
    category: str = "",
    region: str = "",
) -> dict:
    raw_id = station_id or str(data.get("id") or "")
    if raw_id.startswith("radio:"):
        raw_id = raw_id.removeprefix("radio:")

    return {
        "id": raw_id,
        "src": "radio",
        "name": data.get("name") or "",
        "artists": "",
        "album": "",
        "url": (data.get("url") or "").replace("https://", "http://"),
        "cover": (data.get("cover") or data.get("pic") or "").replace("https://", "http://"),
        "duration": None,
        "mv": "",
        "category": category or data.get("category") or "",
        "region": region or data.get("region") or "",
        "resolved_from": "",
    }
