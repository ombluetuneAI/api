# TXB API

FastAPI + Uvicorn 实现的 HTTP API 服务（v2.2.0）。

## 启动

```bash
pip install -r requirements.txt
python run.py
```

默认端口 **8888**。经 Nginx 代理访问：`http://{host}:10074/api/...`

## 配置

使用 `D:/storage/config.json`（可用 `CONFIG_PATH` 覆盖）：

- `qweather.token` — 天气
- `music_path` — 本地音乐目录
- `song_req_cache` — 歌曲请求缓存 CSV
- `local_music_index` — 本地曲库索引 CSV（列：`name,filename`）

首次或曲库批量变更后，在项目根目录执行：

```bash
python scripts/fill_local_music_index.py
```

## 接口域（v1）

| 域 | 前缀 | 说明 |
|----|------|------|
| music | `/music/v1` | 搜索、歌单、点播、随机 |
| radio | `/radio/v1` | 电台随机、点播、热门 |
| pictures | `/pictures/v1` | 随机图片、裁切 |
| videos | `/videos/v1` | 随机 MV |
| content | `/content/v1` | 微博热搜 |
| weather | `/weather/v1` | 天气 |
| proxy | `/proxy/v1` | 随机代理 |

详细设计见 [PRD.md](PRD.md)。

## 音乐 `/music/v1`

统一响应：`{ "code": 200, "data": {}, "message": "ok" }`

| 路径 | 说明 |
|------|------|
| `GET /music/v1/search?keyword=&limit=10` | 搜索 |
| `GET /music/v1/playlists?src=&limit=20&resolve=false` | 歌单 |
| `GET /music/v1/play?keyword=&id=&src=&mid=&source=auto` | 统一取流 |
| `GET /music/v1/random?src=` | 随机一首 |

`source`：`local` / `online` / `auto`（默认）

## 电台 `/radio/v1`

返回字段与 music 相同（电台 `src=radio`，歌曲字段留空）。

| 路径 | 说明 |
|------|------|
| `GET /radio/v1/play?keyword=` | 电台点播 |
| `GET /radio/v1/random` | 随机电台 |
| `GET /radio/v1/favorites` | 热门电台 |

## 测试

```bash
python -m pytest tests/ -q
```
