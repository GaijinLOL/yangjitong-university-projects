# 导入所需依赖
import requests
from bs4 import BeautifulSoup
from aip import AipImageClassify
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import os
import re
import datetime
from flask_pymongo import PyMongo

# 2. 初始化Flask app后，配置MongoDB连接
app = Flask(__name__)
# 配置MongoDB地址（格式：mongodb://用户名:密码@主机:端口/数据库名，本地无密码可简化）
app.config["MONGO_URI"] = "mongodb://localhost:27017/weather_plant_db"  # 这里数据库名是weather_plant_db
mongo = PyMongo(app)  # 初始化MongoDB实例
# 1. 初始化Flask应用 + 跨域配置（解决前端跨域请求）
app = Flask(__name__)
CORS(app)  # 允许所有前端域名请求

# 2. 从环境变量读取百度 AI 植物识别密钥，避免把凭据提交到 Git
APP_ID = os.getenv("BAIDU_APP_ID", "")
API_KEY = os.getenv("BAIDU_API_KEY", "")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")
client = (
    AipImageClassify(APP_ID, API_KEY, SECRET_KEY)
    if all((APP_ID, API_KEY, SECRET_KEY))
    else None
)

# 3. 天气爬取接口（路由：/api/weather，统一5000端口）
@app.route("/api/weather", methods=["GET"])
def crawl_weather():
    try:
        # 目标天气页面URL（上虞百官街道）
        WEATHER_URL = "https://forecast.weather.com.cn/town/weather1dn/101210503001.shtml"
        # 请求头，模拟浏览器访问避免被拦截
        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        # 发送请求获取天气页面
        res = requests.get(WEATHER_URL, headers=HEADERS)
        res.encoding = "utf-8"  # 统一编码防止乱码
        soup = BeautifulSoup(res.text, "lxml")

        # 提取相对湿度（匹配前端展示）
        humidity_elem = soup.find("span", string=lambda text: text and "相对湿度" in text)
        humidity = re.findall(r"\d+", humidity_elem.get_text())[0] if humidity_elem else "--"
        # 提取实时温度
        temp_elem = soup.find("span", class_="temp")  # 定位class为temp的span
        temp = temp_elem.get_text().strip() if temp_elem else "---"  # 直接获取文本（如"0.6"）
        # 提取天气状况（晴/阴/雨等）
        weather_elem = soup.find("i", class_=re.compile(r"weather"), title=re.compile(r"[晴阴雨雪]"))
        weather = weather_elem.get("title").strip() if weather_elem else "---"
        # 提取风向风力
        wind_elem = soup.find("span", string=re.compile(r"[东南西北]风\s*\d+级"))
        wind = wind_elem.get_text().strip() if wind_elem else "--"

        # 返回与前端匹配的字段
        return jsonify({
            "temp": f"{temp}℃",
            "weather": weather,
            "humidity": f"{humidity}%",
            "wind": wind
        })
    except Exception as e:
        # 爬取失败时返回默认值，避免前端报错
        return jsonify({
            "temp": "--℃",
            "weather": "--",
            "humidity": "--%",
            "wind": "--",
            "error": f"天气爬取失败：{str(e)}"
        })

# 4. 植物识别接口（路由：/api/plant，统一5000端口）
@app.route("/api/plant", methods=["POST"])
def plant_recognize():
    try:
        # 接收前端传递的图片Base64数据
        img_base64 = request.form.get("image")
        if not img_base64:
            return jsonify({"plant_name": "error", "confidence": 0.0, "error": "未接收到图片数据"})

        # 解码Base64数据（开启校验，防止无效编码）
        try:
            img_data = base64.b64decode(img_base64, validate=True)
        except base64.binascii.Error:
            return jsonify({"plant_name": "error", "confidence": 0.0, "error": "图片Base64编码错误"})

        # 限制图片大小（最大10MB，避免超大图导致失败）
        if len(img_data) > 10 * 1024 * 1024:
            return jsonify({"plant_name": "error", "confidence": 0.0, "error": "图片超过10MB，请压缩后上传"})

        # 临时保存图片到本地
        with open("temp.jpg", "wb") as f:
            f.write(img_data)

        if client is None:
            return jsonify({
                "plant_name": "未配置",
                "confidence": 0.0,
                "error": "未配置百度 AI 密钥，请设置 BAIDU_APP_ID、BAIDU_API_KEY 和 BAIDU_SECRET_KEY"
            })

        # 调用百度 AI 植物识别接口
        with open("temp.jpg", "rb") as f:
            image = f.read()
        # 发送识别请求（关闭百科返回，提高速度）
        res = client.plantDetect(image, options={"baike_num": 0})
        # 识别完成后删除临时图片
        os.remove("temp.jpg")

        # 解析识别结果
        if "result" in res and len(res["result"]) > 0:
            plant_name = res["result"][0].get("name", "向日葵")
            confidence = round(float(res["result"][0].get("score", 0)) * 100, 2)
            return jsonify({"plant_name": plant_name, "confidence": confidence})
        else:
            return jsonify({"plant_name": "向日葵", "confidence": 0.0, "error": res.get("error_msg", "无识别结果")})
    except Exception as e:
        return jsonify({"plant_name": "向日葵", "confidence": 0.0, "error": f"识别异常：{str(e)}"})


# 5. 启动服务（统一使用5000端口）
if __name__ == "__main__":
    app.run(port=5000, debug=True)  # 端口固定为5000，前端请求统一指向该端口
