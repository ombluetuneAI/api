from __future__ import annotations

import time
from datetime import datetime

import httpx

from app.config import Settings
from app.logging_setup import get_logger

logger = get_logger(__name__)

_cache_weather: dict = {}


async def get_weather(client: httpx.AsyncClient, settings: Settings) -> dict:
    global _cache_weather
    if _cache_weather:
        cache_time = int(
            datetime.fromisoformat(
                _cache_weather.get("now", {}).get("obsTime", "2025-01-17T21:10+08:00")
            ).timestamp()
        )
        if time.time() - cache_time < 10 * 60:
            logger.info("get cache weather")
            return _cache_weather

    url = (
        f"https://devapi.qweather.com/v7/weather/now"
        f"?location={settings.weather_location}&key={settings.qweather_token}"
    )
    r = await client.get(url)
    data = r.json()
    icon = data.get("now", {}).get("icon", "100")
    icon_url = (
        "http://gitee.com/bluetune/esp_sparkbot/raw/master/example/"
        f"factory_demo_v1/weather/{icon}.png"
    )
    data.setdefault("now", {})["icon_url"] = icon_url
    _cache_weather = data
    return data


async def get_qweather(client: httpx.AsyncClient, target_url: str) -> dict:
    r = await client.get(target_url)
    return r.json()
