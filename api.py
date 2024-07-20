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

disallow_type = ["Content-Encoding", "Content-Length", "Date", "Server", "Connection", "Transfer-Encoding", "Access-Control-Allow-Origin", 
                 "Access-Control-Allow-Methods", "Access-Control-Allow-Headers", "Strict-Transport-Security"]

qweather_key = "none"

def config_init():
    global qweather_key

    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    sections = config.sections()
    if ("qweather" in sections):
        options = config.options("qweather")
        if ("key" in options):
            qweather_key = config.get("qweather", "key")
            print(qweather_key)

def csv_read_list(path):

    data = []
    if not os.path.exists(path):
        return data

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for row in reader:
            data.append(row)

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

# def get_netease_music(query):
#     r = requests.get(f"https://api.uomg.com/api/rand.music?sort=%E7%83%AD%E6%AD%8C%E6%A6%9C&format=json")
#     print(r.text)
#     return r.status_code, r.headers, r.content

def netease_get_rand_music():
    info = {
        "name": None,
        "artistsname": None,
        "url": None,
        "picurl": None
    }
    retry_cnt = 10
    while (retry_cnt):
        print(f"request: {retry_cnt}")
        retry_cnt = retry_cnt - 1
        try:
            music =  csv_read_list("netease_music.csv")
            # 读取随机行
            rand_row = random.choice(music)
            info = _audio_csv_2_json(rand_row)
            return info
        except:
            print("get err")
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
#         print(f"request: {retry_cnt}")
#         retry_cnt = retry_cnt - 1
#         try:
#             r = requests.get(f"https://api.cenguigui.cn/api/netease/", timeout=5)
#             name = r.json()["data"]["song_name"]
#             artistsname = r.json()["data"]["artist"]
#             url = r.json()["data"]["play_url"]
#             picurl = r.json()["data"]["img"]
#             print(url)
#             if (url[-3:] != "404" and name and artistsname and url and picurl):
#                 r_data["data"]["name"] = name
#                 r_data["data"]["artistsname"] = artistsname
#                 r_data["data"]["url"] = url.replace("https://", "http://")
#                 r_data["data"]["picurl"] = picurl.replace("https://", "http://")
#                 return r.status_code, r.headers, json.dumps(r_data).encode("utf-8")
#         except:
#             print(f"request err: {retry_cnt}")
#     return None, None, None

def get_rand_music(query):
    music_info = netease_get_rand_music()
    if (music_info):
        r_data = {
            "code": 1,
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
    ids = csv_read_list("fm_id.csv")
    music_infos = fm_get_cur_id_info(random.choice(ids)[0])
    music_info = random.choice(music_infos)
    if (music_info):
        r_data = {
            "code": 1,
            "data": music_info
        }
        return json.dumps(r_data).encode("utf-8")
    return None

def get_favorite_radio(query):
    music_infos = csv_read_list("favorite_radio_table.csv")
    music_info = _audio_csv_2_json(random.choice(music_infos))
    if (music_info):
        r_data = {
            "code": 1,
            "data": music_info
        }
        return json.dumps(r_data).encode("utf-8")
    return None

def get_netease_top_list():
    mp3 = 'http://music.163.com/song/media/outer/url?id='
    lrc = 'http://music.163.com/api/song/lyric?id='

    netease = NetEase()
    all_data = netease.top_songlist()
    csv_data = []

    for data in all_data:
        url = mp3 + str(data['id'])
        lrc_url = lrc + str(data['id']) + '&lv=-1&kv=-1&tv=-1'
        pic_url = data['artists'][0]['picUrl']
        name = data['name']
        artist = data['artists'][0]['name']
        csv_data.append([name, artist, url, pic_url, lrc_url])

    return csv_data

def netease_list_update(file_out):
    print(f"netease_list_update")
    music = get_netease_top_list()
    csv_write_list(file_out, music, "w")

def radio_list_update(file_in, file_out):
    print(f"radio_list_update {file_in}")
    radios = []
    ids = csv_read_list(file_in)
    for id in ids:
        radios += fm_get_cur_id_info_csv(id[0])
    
    csv_write_list(file_out, radios, "w")

def update_task():
    if not os.path.exists("favorite_radio_table.csv"):
        radio_list_update("favorite_radio.csv", "favorite_radio_table.csv")
    if not os.path.exists("netease_music.csv"):
        netease_list_update("netease_music.csv")
    while (1):
        hour = datetime.now(timezone.utc).hour + 8
        if (hour == 2):
            radio_list_update("favorite_radio.csv", "favorite_radio_table.csv")
            netease_list_update("netease_music.csv")
            time.sleep(3600 * 10)
        else:
            time.sleep(1800)

# 自定义的请求处理程序
class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 解析请求路径和参数
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        print(parsed_path, query_params)

        # 获取请求参数值
        path = parsed_path.path
        query = parsed_path.query

        # param1_value = query_params.get('param1', [''])[0]
        # param2_value = query_params.get('param2', [''])[0]

        print(path)
        if (path == "/weather"):
            status_code, header, data = get_weather()
            print(header, len(data))
            self.send_response(status_code)
            self.send_header("Content-Length", len(data))
            for type in header:
                if (type not in disallow_type):
                    self.send_header(type, header[type])
            self.end_headers()
            self.wfile.write(data)
        elif (path == "/qweather"):
            status_code, header, data = get_qweather(query)
            print(header, len(data))
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
        #         print(header, len(data))
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
            data = get_rand_music(query)
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
        elif (path == "/rand_radio"):
            data = get_rand_radio(query)
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
        elif (path == "/favorite_radio"):
            data = get_favorite_radio(query)
            if (data):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)


update_handle = threading.Thread(target=update_task).start()
print("start server")
config_init()
server_address = ('', 8888)
httpd = HTTPServer(server_address, MyHTTPRequestHandler)
httpd.serve_forever()
