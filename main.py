import configparser
import threading
import time
import sys
import csv
import os
import requests
import subprocess
import logging
from datetime import datetime, timedelta, timezone
from proxy import Proxy
from netease import NetEase

run_file = "api.py"

version_url = "https://d.kstore.space/download/3524/server/version"
app_file_url = f"https://d.kstore.space/download/3524/server/{run_file}"
check_update_time = (5 * 60)

file_server_token = "null"
upgrade_task_thread = None

app_task_id = None

def log_init():
    # 配置日志
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            logging.FileHandler('main.log'),  # 文件日志处理器
                            logging.StreamHandler()  # 控制台日志处理器
                        ]
                    )

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

def get_server_version():
    try:
        r = requests.get(version_url, timeout=5)
        if (r.status_code == 200):
            return r.text
        else:
            logging.info("get version err")
            return None
    except:
        return None

def get_local_version():
    f = open("version", "r")
    local_version = f.read()
    f.close()
    return local_version

def update_local_version(version):
    f = open("version", "w+")
    f.write(version)
    f.close()

def update_app_file():
    try:
        data = requests.get(app_file_url, timeout=5).content
        f = open(run_file, "wb+")
        f.write(data)
        f.close()
        return True
    except:
        return False

def config_init():
    global mqtt_server
    global file_server_token

    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    sections = config.sections()
    if ("file sever" in sections):
        options = config.options("file sever")
        if ("token" in options):
            file_server_token = config.get("file sever", "token")
    
    logging.info(file_server_token)

def get_update_period():
    t = 3600
    try:
        with open("update_ploy", "r") as f:
            t = int(f.read())
    except:
        pass
    return t

def run_app(file=run_file):
    global app_task_id
    if (app_task_id != None):
        os.kill(app_task_id, 9)
        time.sleep(1)
    process = subprocess.Popen(["python", file], shell=False)
    app_task_id = process.pid
    logging.info(f"app task id: {app_task_id}")

def check_version():
    if not (datetime.now().hour >= 1 and datetime.now().hour < 8):
        logging.info("main check version")
        version = get_server_version()
        local_version = get_local_version()

        logging.info(f"local version: {local_version}, server version: {version}")
        if (version != None and version != local_version):
            ret = update_app_file()
            if (ret == True):
                update_local_version(version)
                logging.info("start run new app")
                run_app(run_file)
        logging.info("check version end")

def check_app():
    logging.info("main check app")
    err = True
    try:
        r = requests.get(f"http://free.frp.vip:10074/app/hot_fm", timeout=5)
        logging.info(f"result {r.status_code}")
        if (r.status_code == 200):
            err = False
    except:
        logging.info("check app err")
        pass
    if (err == True):
        run_app()
    logging.info("check app end")

# 检查升级
def upgrade_task():
    logging.info("upgrade task running...")
    next_ver_ck_time = time.time() + 60
    next_app_ck_time = time.time() + 60
    ver_sleep = 60
    app_sleep = 60
    
    while (1):
        if (time.time() >= next_ver_ck_time):
            check_version()
            ver_sleep = get_update_period()
            next_ver_ck_time = time.time() + ver_sleep

        if (time.time() >= next_app_ck_time):
            check_app()
            app_sleep = (1800)
            next_app_ck_time = time.time() + app_sleep
        
        min_sleep = min(ver_sleep, app_sleep)
        logging.info(f"main task sleep: {min_sleep}")
        time.sleep(min_sleep)
        logging.info(f"main task wake up")

NETEASE_PLAYLIST_HOT = "./netease/hot.csv"
NETEASE_PLAYLIST_ALL = "./netease/all.csv"
netease_playlist = [NETEASE_PLAYLIST_HOT, NETEASE_PLAYLIST_ALL]

KG_PLAYLIST_HOT = "./kg/hot.csv"

FM_HOT_ID = "./fm/hot_id.csv"
FM_ALL_ID = "./fm/all_id.csv"

FM_PLAYLIST_HOT = "./fm/hot.csv"
FM_PLAYLIST_ALL = "./fm/all.csv"

def get_netease_top_list():
    mp3 = 'http://music.163.com/song/media/outer/url?id='
    lrc = 'http://music.163.com/api/song/lyric?id='

    netease = NetEase()
    all_data = netease.top_songlist()
    csv_data = []

    print(all_data)

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

def radio_list_update(file_in, file_out):
    logging.info(f"radio_list_update {file_in}")
    radios = []
    ids = csv_read_list(file_in)
    for id in ids:
        radios += fm_get_cur_id_info_csv(id[0])
    
    csv_write_list(file_out, radios, "w")

def update_audio_task():
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

def main_task():
    run_app(run_file)
    Proxy().start()
    t1 = threading.Thread(target=upgrade_task)
    t2 = threading.Thread(target=update_audio_task)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def __main__():
    log_init()
    config_init()
    main_task()
    logging.info("exit")

__main__()    
