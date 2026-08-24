from __future__ import annotations

import httpx
from fastapi import Request

from app.config import Settings


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
