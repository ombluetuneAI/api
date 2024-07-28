from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests
import time
import configparser
import json
import os
import csv
import random
from datetime import datetime, timedelta, timezone
import threading
from netease import NetEase
from io import BytesIO
from PIL import Image
from fake_useragent import UserAgent
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

class Proxy:
    def __init__(self):
        self.proxy_pool = []
        r = csv_read_list(PROXY_LIST)
        for i in r:
            self.proxy_pool.append(i[0])
        self.proxy_task_thread = None
    
    def start(self):
        if (self.proxy_task_thread == None):
            self.proxy_task_thread = threading.Thread(target=self._proxy_task)
            self.proxy_task_thread.start()
    
    def stop(self):
        if (self.proxy_task_thread != None):
            self.proxy_task_thread.join()
            self.proxy_task_thread = None

    def get(self):
        ip = None
        if (len(self.proxy_pool)):
            ip = random.choice(self.proxy_pool)
        return ip

    def delete(self, ip):
        self.proxy_pool.remove(ip)
        self._save_proxy()
        logging.info(f"delete proxy({len(self.proxy_pool)}): {ip}")

    def _proxy_task(self):
        next_gen_time = time.time()
        next_check_time = time.time()
        gen_sleep = 3600
        check_sleep = 3600
        while True:
            # 生成新的代理
            if (time.time() >= next_gen_time):
                self._generate_proxy()
                if (len(self.proxy_pool) < 20):
                    gen_sleep = random.randint(1, 60)
                else:
                    gen_sleep = random.randint(1, 600)
                next_gen_time = time.time() + gen_sleep
                logging.info(f"gen sleep {gen_sleep}")
            
            # 重新检查代理是否有效
            if (time.time() >= next_check_time):
                logging.info("timing check proxy pool")
                for ip in self.proxy_pool:
                    if (self._verify_proxy(ip) == False):
                        self.delete(ip)
                check_sleep = 3600 * 2
                next_check_time = time.time() + check_sleep
                logging.info(f"check sleep {check_sleep}")
            
            time.sleep(min(gen_sleep, check_sleep) + 2)
            gen_sleep = 3600
            check_sleep = 3600

    def _save_proxy(self):
        w_data = []
        for i in self.proxy_pool:
            w_data.append([i])
        csv_write_list(PROXY_LIST, w_data, "w")

    def _add_proxy(self, ip):
        if (ip not in self.proxy_pool):
            self.proxy_pool.append(ip)
            logging.info(f"add proxy({len(self.proxy_pool)}): {ip}")
            self._save_proxy()

    def _generate_proxy(self):
        logging.info("generate proxy")
        ip = self.get()
        proxies = None
        if (ip != None):
            proxies = {"http": "http://{}".format(ip)}
        try:
            ip = requests.get("http://demo.spiderpy.cn/get/", proxies=proxies, timeout=5, headers={'User-Agent':str(UserAgent().random)}).json().get("proxy")
            if (ip):
                if (self._verify_proxy(ip) == True):
                    self._add_proxy(ip)
        except:
            logging.info("generate proxy error")

    def _verify_proxy(self, proxy):
        ret = False
        try:
            r = requests.get("http://icanhazip.com/", proxies={"http": "http://{}".format(proxy)}, timeout=2, headers={'User-Agent':str(UserAgent().random)})
            if (r.status_code == 200):
                if (r.text.replace("\n", "") == str(proxy.split(":")[0])):
                    ret = True
        except:
            pass
        if (ret == False):
            logging.info(f"verify {proxy} error")
        return ret

def log_init():
    # 配置日志
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
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


location = "113.96,22.57"
def get_weather():
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?location={location}&key={qweather_key}")
    return r.status_code, r.headers, r.content

def get_qweather(query):
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?{query}")
    return r.status_code, r.headers, r.content

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
            
            info_url = f"http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={info['url']}"
            data = requests.get(info_url).json()
            url = data.get("url").replace("https", "http")
            pic_url = data.get("imgUrl").replace("{size}", "666")
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
#                 return r.status_code, r.headers, json.dumps(r_data).encode("utf-8")
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
        return json.dumps(r_data).encode("utf-8")
    return None

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

def get_rand_radio(query):
    ids = csv_read_list(FM_ALL_ID)
    music_infos = fm_get_cur_id_info(random.choice(ids)[0])
    music_info = random.choice(music_infos)
    if (music_info):
        r_data = {
            "code": 200,
            "data": music_info
        }
        return json.dumps(r_data).encode("utf-8")
    return None

def get_favorite_radio(query):
    music_infos = csv_read_list(FM_PLAYLIST_HOT)
    music_info = _audio_csv_2_json(random.choice(music_infos))
    if (music_info):
        r_data = {
            "code": 200,
            "data": music_info
        }
        return json.dumps(r_data).encode("utf-8")
    return None

def pic_resize(pic_url, w, h):
    r = requests.get(pic_url)
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

def get_netease_top_list():
    mp3 = 'http://music.163.com/song/media/outer/url?id='
    lrc = 'http://music.163.com/api/song/lyric?id='

    netease = NetEase()
    all_data = netease.top_songlist()
    csv_data = []

    for data in all_data:
        url = mp3 + str(data['id'])
        lrc_url = lrc + str(data['id']) + '&lv=-1&kv=-1&tv=-1'
        pic_url = data["album"]["picUrl"]
        name = data['name']
        artist = data['artists'][0]['name']
        csv_data.append([name, artist, url, pic_url, lrc_url])

    return csv_data

def netease_list_update(file_out):
    logging.info(f"netease_list_update")
    music = get_netease_top_list()
    csv_write_list(file_out, music, "w")

def radio_list_update(file_in, file_out):
    logging.info(f"radio_list_update {file_in}")
    radios = []
    ids = csv_read_list(file_in)
    for id in ids:
        radios += fm_get_cur_id_info_csv(id[0])
    
    csv_write_list(file_out, radios, "w")

def update_task():
    if not os.path.exists(FM_PLAYLIST_HOT):
        radio_list_update(FM_HOT_ID, FM_PLAYLIST_HOT)
    if not os.path.exists(NETEASE_PLAYLIST_HOT):
        netease_list_update(NETEASE_PLAYLIST_HOT)
    while (1):
        # 北京时间
        hour = (datetime.now(timezone.utc).hour + 8) % 24
        if (hour == 2):
            radio_list_update(FM_HOT_ID, FM_PLAYLIST_HOT)
            netease_list_update(NETEASE_PLAYLIST_HOT)
            time.sleep(3600 * 10)
        else:
            time.sleep(1800)

# 自定义的请求处理程序
class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 解析请求路径和参数
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parsed_path.query
        query_params = parse_qs(query)
        
        logging.info(parsed_path)
        
        if (path == "/weather"):
            status_code, header, data = get_weather()
            self.send_response(status_code)
            self.send_header("Content-Length", len(data))
            for type in header:
                if (type not in disallow_type):
                    self.send_header(type, header[type])
            self.end_headers()
            self.wfile.write(data)
        elif (path == "/qweather"):
            status_code, header, data = get_qweather(query)
            self.send_response(status_code)
            self.send_header("Content-Length", len(data))
            for type in header:
                if (type not in disallow_type):
                    self.send_header(type, header[type])
            self.end_headers()
            self.wfile.write(data)
        # elif (path == "/netease_music"):
        #     status_code, header, data = get_netease_music(query)
        #     if (data):
        #         self.send_response(status_code)
        #         self.send_header("Content-Length", len(data))
        #         for type in header:
        #             if (type not in disallow_type):
        #                 self.send_header(type, header[type])
        #         self.end_headers()
        #         self.wfile.write(data)
        #     else:
        #         self.send_response(404)
        #         self.end_headers()
        elif (path == "/rand_music"):
            data = get_rand_music()
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
        elif (path == "/rand_radio" or path == "/rand_fm"):
            data = get_rand_radio(query)
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
        elif (path == "/favorite_radio" or path == "/hot_fm"):
            data = get_favorite_radio(query)
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
        elif (path == "/pic_resize"):
            pic_url = query_params.get('url', [''])[0]
            width = int(query_params.get('w', [''])[0])
            height = int(query_params.get('h', [''])[0])
            image,format = pic_resize(pic_url, width, height)
            if (image):
                self.send_response(200)
                self.send_header("Content-Type", f"image/{format}")
                self.send_header("Content-Length", len(image))
                self.end_headers()
                self.wfile.write(image)
            else:
                self.send_response(404)
        elif (path == "/proxy"):
            url = query_params.get('url', [''])[0]
            list = {}
            if (os.path.exists("http_remap.json")):
                with open("http_remap.json", "r", encoding="utf-8") as f:
                    list = json.load(f)
            if ('http' not in url):
                url = f'http://{url}'
            for a in list:
                if (a in url):
                    url = url.replace(a, list[a])
            logging.info(f"request: {url}")
            response = requests.get(url)
            self.send_response(200)
            self.send_header('Content-type', response.headers['Content-Type'])
            self.end_headers()
            self.wfile.write(response.content)
        elif (path == "/update_list"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"exec update_list finished")
            radio_list_update(FM_HOT_ID, FM_PLAYLIST_HOT)
            netease_list_update(NETEASE_PLAYLIST_HOT)
        elif (path == "/get_proxy"):
            if (en_proxy_task == True):
                ip = proxy.get()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(ip.encode())
            else:
                self.send_response(404)
            
log_init()
config_init()
if (en_proxy_task == True):
    proxy = Proxy()
    proxy.start()
update_handle = threading.Thread(target=update_task).start()
logging.info("start server")
server_address = ('', 8888)
httpd = HTTPServer(server_address, MyHTTPRequestHandler)
httpd.serve_forever()

