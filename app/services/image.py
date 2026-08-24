from __future__ import annotations

import asyncio
import random
from io import BytesIO

import httpx
from PIL import Image

from app.logging_setup import get_logger
from app.utils.csv_io import csv_read_list

logger = get_logger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
)

# 审计通过: imgapi.cn, api.suyanw.cn
RAND_PIC_URLS = [
    "https://imgapi.cn/api.php",
    "https://api.suyanw.cn/api/meinv.php",
]


def _resize_image(content: bytes, w: int, h: int) -> tuple[bytes | None, str | None]:
    img_io = BytesIO(content)
    img = Image.open(img_io)
    final_img = img
    if w and h:
        src_w, src_h = img.size
        src_ratio = src_w / src_h
        target_ratio = w / h
        if src_ratio > target_ratio:
            interim_h = h
            interim_w = int(interim_h * src_ratio)
        else:
            interim_w = w
            interim_h = int(interim_w / src_ratio)
        resized_img = img.resize((interim_w, interim_h), Image.LANCZOS)
        left = (interim_w - w) // 2
        top = (interim_h - h) // 2
        final_img = resized_img.crop((left, top, left + w, top + h))
    out = BytesIO()
    img_format = img.format or "JPEG"
    if img_format == "WEBP":
        img_format = "JPEG"
    final_img.save(out, img_format)
    return out.getvalue(), img_format.lower()


async def pic_resize(
    client: httpx.AsyncClient, pic_url: str, w: int, h: int
) -> tuple[bytes | None, str | None]:
    r = await client.get(pic_url, headers={"User-Agent": UA}, timeout=5.0)
    if r.status_code != 200:
        return None, None
    logger.info("%s resize -> %s*%s", pic_url, w, h)
    return await asyncio.to_thread(_resize_image, r.content, w, h)


async def get_rand_pic(
    client: httpx.AsyncClient, width: int, height: int
) -> tuple[bytes | None, str | None]:
    pic_url = random.choice(RAND_PIC_URLS)
    logger.info(pic_url)
    return await pic_resize(client, pic_url, width, height)


def get_random_proxy(proxy_list_path: str) -> str | None:
    proxy_pool = csv_read_list(proxy_list_path)
    if not proxy_pool:
        return None
    return random.choice(proxy_pool)[0]
