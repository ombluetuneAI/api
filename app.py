from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests
import time
import configparser

disallow_type = ["Content-Encoding", "Content-Length", "Date", "Server"]

qweather_key = "none"

def config_init():
    global file_server_token
    global qweather_key

    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    sections = config.sections()
    if ("file sever" in sections):
        options = config.options("file sever")
        if ("token" in options):
            file_server_token = config.get("file sever", "token")
    if ("qweather" in sections):
        options = config.options("qweather")
        if ("key" in options):
            qweather_key = config.get("qweather", "key")
    
    print(file_server_token, qweather_key)


location = "113.96,22.57"
def get_weather():
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?location={location}&key={qweather_key}")
    return r.status_code, r.headers, r.content

def get_qweather(query):
    r = requests.get(f"https://devapi.qweather.com/v7/weather/now?{query}")
    return r.status_code, r.headers, r.content

def get_netease_music(query):
    r = requests.get(f"https://api.uomg.com/api/rand.music?sort=%E7%83%AD%E6%AD%8C%E6%A6%9C&format=json")
    print(r.text)
    return r.status_code, r.headers, r.content

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
        elif (path == "/netease_music"):
            status_code, header, data = get_netease_music(query)
            print(header, len(data))
            self.send_response(status_code)
            self.send_header("Content-Length", len(data))
            for type in header:
                if (type not in disallow_type):
                    self.send_header(type, header[type])
            self.end_headers()
            self.wfile.write(data)

config_init()
server_address = ('', 8888)
httpd = HTTPServer(server_address, MyHTTPRequestHandler)
httpd.serve_forever()
