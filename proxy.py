import requests
import os
import csv
import random
import time
import logging
import threading
from datetime import datetime
from fake_useragent import UserAgent

class Proxy:
    def __init__(self):
        self.proxy_pool = []
        self.PROXY_LIST = "./proxy_pool.csv"
        self.proxy_pool = self.csv_read_list(self.PROXY_LIST)
        self.proxy_thread = None
    
    def start(self):
        if (self.proxy_thread == None):
            self.proxy_thread = threading.Thread(target=self._proxy_task)
            self.proxy_thread.start()
            logging.info("proxy task start")
    
    def stop(self):
        if (self.proxy_thread != None):
            self.proxy_thread = None

    def get(self):
        ip = None
        if (len(self.proxy_pool)):
            ip = random.choice(self.proxy_pool)[0]
        return ip

    def delete(self, ip):
        for _ in self.proxy_pool:
            if (ip == _[0]):
                self.proxy_pool.remove(_)
        self._save_proxy()
        logging.info(f"delete proxy({len(self.proxy_pool)}): {ip}")

    def _proxy_task(self):
        next_gen_time = time.time() + 30
        next_check_time = time.time() + 10
        gen_sleep = 10
        check_sleep = 10
        while True:
            
            # 定时检查代理是否有效
            if (time.time() >= next_check_time):
                logging.info("timing check proxy pool")
                for _ in self.proxy_pool:
                    if (self._verify_proxy(_[0]) == False):
                        self.delete(_[0])
                check_sleep = 3600 * 2
                next_check_time = time.time() + check_sleep
                logging.info(f"check sleep {check_sleep}")

            # 生成新的代理
            if (time.time() >= next_gen_time):
                self._generate_proxy()
                if (len(self.proxy_pool) < 10):
                    gen_sleep = random.randint(30, 120)
                elif (len(self.proxy_pool) < 20):
                    gen_sleep = random.randint(60, 300)
                else:
                    gen_sleep = random.randint(60, 1000)
                next_gen_time = time.time() + gen_sleep
                logging.info(f"gen sleep {gen_sleep}")
            
            sleep_time = min(gen_sleep, check_sleep)
            logging.info(f"sleep {sleep_time}")
            time.sleep(sleep_time)

    def _save_proxy(self):
        self.csv_write_list(self.PROXY_LIST, self.proxy_pool, "w")
    
    def _find_proxy(self, ip):
        for _ in self.proxy_pool:
            if (ip == _[0]):
                return True
        return False

    def _add_proxy(self, ip):
        if (self._find_proxy(ip) == False):
            self.proxy_pool.append([ip, datetime.now()])
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
            print(ip)
            if (ip):
                if (self._verify_proxy(ip) == True):
                    self._add_proxy(ip)
        except:
            logging.info("proxy error")

    def _verify_proxy(self, proxy):
        ret = False
        try:
            r = requests.get("http://icanhazip.com/", proxies={"http": "http://{}".format(proxy)}, timeout=3, headers={'User-Agent':str(UserAgent().random)})
            if (r.status_code == 200):
                if (r.text.replace("\n", "") == str(proxy.split(":")[0])):
                    ret = True
        except:
            pass
        if (ret == False):
            logging.info(f"verify {proxy} error")
        return ret
    
    def csv_read_list(self, path):

        data = []
        if not os.path.exists(path):
            return data

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            for row in reader:
                data.append(row)

        return data

    def csv_write_list(self, path, user_data, mode):
        if (len(user_data) == 0):
            return
        f = open(path, mode, encoding="utf-8", newline="")
        csv_write = csv.writer(f)
        csv_write.writerows(user_data)
  