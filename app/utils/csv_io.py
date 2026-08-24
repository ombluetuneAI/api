from __future__ import annotations

import csv
import os

import portalocker


def csv_read_list(path: str) -> list[list[str]]:
    data: list[list[str]] = []
    if not os.path.exists(path):
        return data
    with portalocker.Lock(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)
    return data


def csv_write_list(path: str, user_data: list[list[str]], mode: str) -> None:
    with portalocker.Lock(path, mode, encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(user_data)
