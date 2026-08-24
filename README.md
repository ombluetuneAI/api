# TXB API

FastAPI + Uvicorn 实现的 HTTP API 服务。

## 启动

```bash
pip install -r requirements.txt
python run.py
```

默认端口 **8888**。如需临时改用其他端口，可设置环境变量：

```bash
set API_PORT=1234
python run.py
```

## 配置

继续使用 `F:/storage/config.json`（可用 `CONFIG_PATH` 覆盖）。API 读取字段：

- `qweather.token` — 天气
- `music_path` — 本地音乐目录
- `song_req_cache` — 歌曲请求缓存 CSV

## 数据目录

```
data/fm/           # 电台源数据（API 读取）
  all_id.csv       # /rand_radio 使用
  hot_id.csv       # 生成 cache/fm/hot.csv 的输入
  sources/         # 爬取用的分类电台列表（API 不读）
cache/             # 运行时缓存（gitignore）
```

## 接口

| 路径 | 说明 |
|------|------|
| `/health` | 健康检查 |
| `/weather` | 和风天气 |
| `/qweather` | 透传外部天气 URL（`?url=`） |
| `/rand_music` | 随机音乐 |
| `/rand_radio` `/rand_fm` | 随机电台 |
| `/favorite_radio` `/hot_fm` | 热门电台 |
| `/rand_mv` | MV 重定向 |
| `/rand_pic` | 随机图片 |
| `/pic_resize` | 图片裁切 |
| `/get_proxy` | 随机代理 IP |
| `/dailyhot` | 微博热搜 |
| `/music` | 本地音乐匹配 |
| `/api/{src}` | 音乐 URL 解析（当前有效源：`kw`） |
