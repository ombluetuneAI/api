from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    config_path: str = Field(default="D:/storage/config.json", validation_alias="CONFIG_PATH")
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8888, validation_alias="API_PORT")
    api_root_path: str = Field(default="/api", validation_alias="API_ROOT_PATH")
    weather_location: str = "113.96,22.57"
    music_files_base_url: str = "http://192.168.10.138:10074/files/music"

    fm_hot_id: str = "./data/fm/hot_id.csv"
    fm_all_id: str = "./data/fm/all_id.csv"
    fm_sources_dir: str = "./data/fm/sources"
    fm_playlist_hot: str = "./cache/fm/hot.csv"
    netease_playlist_hot: str = "./cache/wy/hot.csv"
    kg_playlist_hot: str = "./cache/kg/hot.csv"
    kw_playlist_hot: str = "./cache/kw/hot.csv"
    tx_playlist_hot: str = "./cache/tx/hot.csv"
    proxy_list: str = "./cache/proxy_pool.csv"
    song_req_cache: str = "./cache/song_req_cache.csv"
    local_music_index: str = "./cache/local_music_index.csv"

    @property
    def runtime(self) -> dict:
        path = Path(self.config_path)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @property
    def qweather_token(self) -> str:
        return self.runtime.get("qweather", {}).get("token", "")

    @property
    def music_path(self) -> str:
        return self.runtime.get("music_path", "")

    @property
    def song_req_cache_file(self) -> str:
        return self.runtime.get("song_req_cache", self.song_req_cache)

    @property
    def local_music_index_file(self) -> str:
        return self.runtime.get("local_music_index", self.local_music_index)


@lru_cache
def get_settings() -> Settings:
    return Settings()
