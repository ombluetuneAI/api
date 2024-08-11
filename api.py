from aiohttp import web
from urllib.parse import urlparse, parse_qs
import requests
import time
import configparser
import json
import os
import csv
import random
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import logging

disallow_type = ["Content-Encoding", "Content-Length", "Date", "Server", "Connection", "Transfer-Encoding", "Access-Control-Allow-Origin", 
                 "Access-Control-Allow-Methods", "Access-Control-Allow-Headers", "Strict-Transport-Security"]

qweather_key = "none"
proxy = None
en_proxy_task = False

NETEASE_PLAYLIST_HOT = "./netease/hot.csv"
NETEASE_PLAYLIST_ALL = "./netease/all.csv"
netease_playlist = [NETEASE_PLAYLIST_HOT, NETEASE_PLAYLIST_ALL]

KG_PLAYLIST_HOT = "./kg/hot.csv"

FM_HOT_ID = "./fm/hot_id.csv"
FM_ALL_ID = "./fm/all_id.csv"

FM_PLAYLIST_HOT = "./fm/hot.csv"
FM_PLAYLIST_ALL = "./fm/all.csv"

PROXY_LIST = "./proxy_pool.csv"

def log_init():
    # 配置日志
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            logging.FileHandler('run.log'),  # 文件日志处理器
                            logging.StreamHandler()  # 控制台日志处理器
                        ]
                    )
    
def config_init():
    global qweather_key
    global en_proxy_task

    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    sections = config.sections()
    if ("qweather" in sections):
        options = config.options("qweather")
        if ("key" in options):
            qweather_key = config.get("qweather", "key")
            logging.info(qweather_key)
    if ("proxy" in sections):
        options = config.options("proxy")
        if ("enable" in options):
            en_proxy_task = (config.get("proxy", "enable") == "1")

def csv_read_list(path):

    data = []
    if not os.path.exists(path):
        return data

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for row in reader:
            data.append(row)

    return data

def csv_read_multi_list(paths):
    data = []
    for path in paths:
        data += csv_read_list(path)
    return data

def csv_write_list(path, user_data, mode):
    if (len(user_data) == 0):
        return
    f = open(path, mode, encoding="utf-8", newline="")
    csv_write = csv.writer(f)
    csv_write.writerows(user_data)

def _audio_csv_2_json(csv_data):
    info = {
        "name": csv_data[0],
        "artistsname": csv_data[1],
        "url": csv_data[2],
        "picurl": csv_data[3]
    }
    return info

msuic_src = ["qq", "kg", "kw", "wy"]

"""
成功消息示例
{
    "code": 0,
    "msg": "success", 
    "url": "http://fs.youthandroid2.kugou.com/xxxxx.mp3'
}
"""
music_err_url_rsp = {
    "code": 1,
    "msg": "未知错误"
}

def _music_url_api_1(src, id, mid, quality='128k'):
    # 音乐源1
    url = f"https://render.niuma666bet.buzz/url/{src}/{id}/{quality}"
    headers = {
        "X-Request-Key": "share-v2"
    }
    try:
        logging.info(f"request: {url}")
        data = requests.get(url, headers=headers).json()
    except:
        data = music_err_url_rsp
    return data

def _music_url_api_2(src, id, mid, quality='320k'):
    src_table = {
        "tx": "qqmusic",
        "kw": "kuwo",
        "mg": "mgmusic"
    }

    if (src not in src_table or quality != '320k'): return music_err_url_rsp

    # 音乐源1
    url = f"https://api.leafone.cn/api/{src_table[src]}?id={mid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        logging.info(f"request: {url}")
        _ = requests.get(url, headers=headers).json()
        data = {
            "code": 0,
            "msg": "success", 
            "url": _.get("data", []).get("url", "")
        }
    except:
        data = music_err_url_rsp
    return data

def music_url_api(src, id, mid='', quality='128k'):
    api_fun = [_music_url_api_1, _music_url_api_2]
    for api in api_fun:
        data = api(src, id, mid, quality)
        if (data.get("msg", "") == "success"):
            return data
    return music_err_url_rsp


location = "113.96,22.57"
def get_weather():
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?location={location}&key={qweather_key}")
    return r.json()

def get_qweather(query):
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?{query}")
    return r.json()

def kg_get_rand_music():
    retry_cnt = 10
    while (retry_cnt):
        logging.info(f"request: {retry_cnt}")
        retry_cnt = retry_cnt - 1
        try:
            music =  csv_read_list(KG_PLAYLIST_HOT)
            # 读取随机行
            rand_row = random.choice(music) + ["pic_url"]
            info = _audio_csv_2_json(rand_row)
            hash = info.get("url")

            data = music_url_api('kg', hash, quality="320k")
            
            # info_url = f"http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={info['url']}"
            # data = requests.get(info_url).json()
            url = data.get("url").replace("https", "http")
            pic_url = data.get("imgUrl", "").replace("{size}", "666")
            if (len(url)):
                info["url"] = url
                info["picurl"] = pic_url
                return info
        except:
            logging.info("get err")
    return None

# def get_netease_music(query):
#     r = requests.get(f"https://api.uomg.com/api/rand.music?sort=%E7%83%AD%E6%AD%8C%E6%A6%9C&format=json")
#     logging.info(r.text)
#     return r.status_code, r.headers, r.content

def netease_get_rand_music():
    retry_cnt = 10
    while (retry_cnt):
        logging.info(f"request: {retry_cnt}")
        retry_cnt = retry_cnt - 1
        try:
            music =  csv_read_multi_list(netease_playlist)
            # 读取随机行
            rand_row = random.choice(music)
            info = _audio_csv_2_json(rand_row)
            
            r = requests.get(info["url"])
            if (r.url[-3:] != "404"):
                info["url"] = r.url
                return info
        except:
            logging.info("get err")
    return None

# def get_netease_music(query):
#     r_data = {"code": 1,
#               "data":{
#                   "name": None,
#                   "artistsname": None,
#                   "url": None,
#                   "picurl": None
#               }
#             }
#     retry_cnt = 3
#     while (retry_cnt):
#         logging.info(f"request: {retry_cnt}")
#         retry_cnt = retry_cnt - 1
#         try:
#             r = requests.get(f"https://api.cenguigui.cn/api/netease/", timeout=5)
#             name = r.json()["data"]["song_name"]
#             artistsname = r.json()["data"]["artist"]
#             url = r.json()["data"]["play_url"]
#             picurl = r.json()["data"]["img"]
#             logging.info(url)
#             if (url[-3:] != "404" and name and artistsname and url and picurl):
#                 r_data["data"]["name"] = name
#                 r_data["data"]["artistsname"] = artistsname
#                 r_data["data"]["url"] = url.replace("https://", "http://")
#                 r_data["data"]["picurl"] = picurl.replace("https://", "http://")
#                 return r.status_code, r.headers, r_data
#         except:
#             logging.info(f"request err: {retry_cnt}")
#     return None, None, None

def get_rand_music():
    rand_music_list = [netease_get_rand_music, kg_get_rand_music]
    music_info = random.choice(rand_music_list)()
    if (music_info):
        r_data = {
            "code": 200,
            "data": music_info
        }
        return r_data
    return {"code": 404}

def fm_get_cur_id_info(id):
    music_infos = []
    r = requests.get(f"https://webapi.qingting.fm/api/pc/radio/{id}")
    data = r.json()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    if (data["album"] == []):
        return []
    picurl = data["album"]["cover"]
    artistsname = data["album"]["title"]

    today = datetime.now().weekday()
    today = (today + 1) if (today + 1) <= 6 else 7  

    d_data = data["pList"][str(today)]
    for i in d_data:
        name = i["title"]
        start_time = i["start_time"].replace(":", "")
        end_time = i["end_time"].replace(":", "")
        url = f"http://lcache.qtfm.cn/cache/{yesterday}/{id}/{id}_{yesterday}_{start_time}_{end_time}_24_0.aac"
        music_infos.append({
            "name": name,
            "artistsname": artistsname,
            "url": url,
            "picurl": picurl
        })
    return music_infos

def fm_get_cur_id_info_csv(id):
    music_infos = []
    r = requests.get(f"https://webapi.qingting.fm/api/pc/radio/{id}")
    data = r.json()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    if (data["album"] == []):
        return []
    picurl = data["album"]["cover"]
    artistsname = data["album"]["title"]

    today = datetime.now().weekday()
    today = (today + 1) if (today + 1) <= 6 else 7  

    d_data = data["pList"][str(today)]
    for i in d_data:
        name = i["title"]
        start_time = i["start_time"].replace(":", "")
        end_time = i["end_time"].replace(":", "")
        url = f"http://lcache.qtfm.cn/cache/{yesterday}/{id}/{id}_{yesterday}_{start_time}_{end_time}_24_0.aac"
        music_infos.append([name,artistsname, url, picurl])
    return music_infos

def get_rand_radio():
    ids = csv_read_list(FM_ALL_ID)
    music_infos = fm_get_cur_id_info(random.choice(ids)[0])
    music_info = random.choice(music_infos)
    if (music_info):
        r_data = {
            "code": 200,
            "data": music_info
        }
        return r_data
    return {"code": 404}

def get_favorite_radio():
    music_infos = csv_read_list(FM_PLAYLIST_HOT)
    music_info = _audio_csv_2_json(random.choice(music_infos))
    if (music_info):
        r_data = {
            "code": 200,
            "data": music_info
        }
        return r_data
    return {"code": 404}

def pic_resize(pic_url, w, h):
    r = requests.get(pic_url, timeout=5)
    if (r.status_code == 200):
        img_io = BytesIO(r.content)
        img = Image.open(img_io)
        if (w > h and img.width > w):
            height = h
            width = int(img.width * height / img.height)
        elif (w <= h and img.height > h):
            width = w
            height = int(img.height * width / img.width)
        else:
            return img_io.getvalue(), img.format.lower()
        logging.info(f"{img.width}*{img.height} to {width}*{height}")
        resize_image = img.resize((width, height))
        img_out_io = BytesIO()
        resize_image.save(img_out_io, img.format)
        return img_out_io.getvalue(), img.format.lower()
    else:
        return None, None

def music_api(src, params):
    id = params.get("id")
    mid = params.get("mid", "")
    quality = params.get("quality", ['128k'])
    data = music_url_api(src, id, mid, quality)
    return data

async def handle_request_api(req):
    logging.info(f"req {req.url}")
    src = req.match_info['src']
    query = req.query
    data = music_api(src, query)
    return web.json_response(data)

# 自定义的请求处理程序
async def handle_request(req):
    path = req.path
    query = req.query

    logging.info(f"req {req.url}")

    if (path == "/weather"):
        data = get_weather()
        return web.json_response(data)
    elif (path == "/qweather"):
        data = get_qweather(query)
        return web.json_response(data)
    elif (path == "/rand_music"):
        data = get_rand_music()
        return web.json_response(data)
    elif (path == "/rand_radio" or path == "/rand_fm"):
        data = get_rand_radio()
        return web.json_response(data)
    elif (path == "/favorite_radio" or path == "/hot_fm"):
        data = get_favorite_radio()
        return web.json_response(data)
    elif (path == "/get_proxy"):
        proxy_pool = csv_read_list(PROXY_LIST)
        ip = random.choice(proxy_pool)[0]
        return web.Response(status=200, text=ip, content_type="text/plain")
    elif (path == "/pic_resize"):
        pic_url = query.get('url', "")
        width = int(query.get('w', 100))
        height = int(query.get('h', 100))
        image,format = pic_resize(pic_url, width, height)
        if (image):
            return web.Response(body=image, content_type=f"image/{format}")
        else:
            return web.Response(status=404)
    elif (path == "/update_ploy"):
        time = query.get('time', "3600")
        with open("update_ploy", "w") as f:
            f.write(time)
        return web.Response(status=200, text="update_ploy", content_type="text/plain")

api_get_param = ['/qweather', '/weather', '/rand_music', '/rand_radio', '/rand_fm', '/favorite_radio', '/hot_fm', '/get_proxy', '/pic_resize', '/api', '/update_ploy']

log_init()
config_init()
# update_handle = threading.Thread(target=update_task).start()
logging.info("start server")
app = web.Application()
for p in api_get_param:
    app.router.add_get(p, handle_request)

app.router.add_get('/api/{src}', handle_request_api)

web.run_app(app, host='127.0.0.1', port=8888)
