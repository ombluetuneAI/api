from __future__ import annotations

import re
from datetime import datetime

import httpx


def parse_hot_num(value) -> int:
    if value is None:
        return 0
    text = str(value).replace(",", "")
    nums = re.findall(r"\d+", text)
    if not nums:
        return 0
    hot = int(nums[0])
    if "万" in text and hot < 10000:
        hot *= 10000
    return hot


async def fetch_dailyhot(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    url = "https://api.qqsuu.cn/api/dm-weibohot"
    r = await client.get(url, timeout=10.0)
    r.raise_for_status()
    raw = r.json()
    news = []
    for item in raw.get("data", {}).get("list", []):
        news.append({
            "title": item.get("hotword", ""),
            "hot": parse_hot_num(item.get("hotwordnum", "")),
        })
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return news, update_time
