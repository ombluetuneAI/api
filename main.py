import configparser
import threading
import time
import sys
import os
import requests
import subprocess
from datetime import datetime

run_file = "api.py"

version_url = "https://d.kstore.space/download/3524/server/version"
app_file_url = f"https://d.kstore.space/download/3524/server/{run_file}"
check_update_time = (5 * 60)

file_server_token = "null"
upgrade_task_thread = None

stop_app_task = False
app_task_id = None

def get_server_version():
    try:
        r = requests.get(version_url)
        if (r.status_code == 200):
            return r.text
        else:
            print("get version err")
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
        data = requests.get(app_file_url).content
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
    
    print(file_server_token)

def run_app(file):
    global app_task_id
    if (app_task_id != None):
        os.kill(app_task_id, 9)
        time.sleep(1)
    process = subprocess.Popen(["python", file], shell=False)
    app_task_id = process.pid
    print(f"app task id: {app_task_id}")

# 检查升级
def upgrade_task():
    global stop_app_task
    print("upgrade task running...")
    
    while (1):
        if not (datetime.now().hour >= 1 and datetime.now().hour < 8):
            version = get_server_version()
            local_version = get_local_version()

            print(f"local version: {local_version}, server version: {version}")
            if (version != None and version != local_version):
                ret = update_app_file()
                if (ret == True):
                    update_local_version(version)
                    stop_app_task = True
                    print("start run new app")
                    run_app(run_file)
        
        time.sleep(check_update_time)

def main_task():
    run_app(run_file)
    # 创建升级任务
    upgrade_task_thread = threading.Thread(target=upgrade_task)
    upgrade_task_thread.start()
    while (stop_app_task != True):
        time.sleep(1)
    
    if (app_task_id != None):
        os.kill(app_task_id, 9)
        time.sleep(1)


def __main__():
    config_init()
    main_task()
    print("exit")

__main__()    
