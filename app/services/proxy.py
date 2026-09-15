from __future__ import annotations

import random

from app.utils.csv_io import csv_read_list


def get_random_proxy(proxy_list_path: str) -> str | None:
    proxy_pool = csv_read_list(proxy_list_path)
    if not proxy_pool:
        return None
    return random.choice(proxy_pool)[0]
