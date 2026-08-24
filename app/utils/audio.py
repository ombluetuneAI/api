from __future__ import annotations

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def audio_csv_to_json(csv_data: list[str]) -> dict:
    pic = csv_data[3] if len(csv_data) >= 4 else ""
    return {
        "name": csv_data[0],
        "artists": csv_data[1],
        "url": csv_data[2],
        "pic": pic,
        "mv": "",
    }
