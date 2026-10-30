app.py 使用说明
1. 安装依赖（app.py）
在命令行执行以下命令，安装`app.py`运行所需的依赖包：
pip install requests beautifulsoup4 baidu-aip flask flask-cors flask-pymongo pymongo
pip install library
2. 运行app.py
- 确保本地已启动MongoDB服务（默认端口为27017）；若未安装MongoDB，需先完成安装并启动服务。
- 百度 AI 植物识别使用环境变量 `BAIDU_APP_ID`、`BAIDU_API_KEY`、`BAIDU_SECRET_KEY`；请复制项目根目录的 `.env.example` 后在本机填写，**不要把真实密钥写入代码或提交到 Git**。


2.2 启动服务
进入`app.py`所在的`backend`目录，在命令行执行以下命令启动Flask后端服务：python app.py
启动成功后，服务会运行在`5000`端口，前端可向该端口发起接口请求。

3. 常见问题及解决
问题1：依赖包缺失报错（如“No module named 'xxx'”）
解决：
根据报错提示的缺失包名，执行`pip install 缺失包名`（例如缺失`flask`则执行`pip install flask`）。

问题2：MongoDB连接失败
解决：
1. 检查本地MongoDB服务是否处于启动状态（Windows可通过“服务”查看，Linux/macOS执行`mongod`启动）；
2. 确认`app.config["MONGO_URI"]`中的地址、端口、数据库名与本地MongoDB配置一致（默认配置：`mongodb://localhost:27017/weather_plant_db`）。


问题3：百度AI植物识别接口调用失败
解决：
1. 核对`APP_ID`、`API_KEY`、`SECRET_KEY`是否与百度AI开放平台对应应用的密钥完全一致；
2. 确认百度AI开放平台中该应用已开通“植物识别”能力。

问题4：图片上传/识别报错（如“Base64编码错误”“图片超过10MB”）
解决：
1. 前端传递的图片Base64编码需确保格式完整、无多余字符；
2. 上传图片需压缩至10MB以内后，再进行Base64编码传递。

4. 接口说明
天气信息接口
- 接口路径：`/api/weather`
- 请求方式：`GET`
- 返回示例（成功）：
```json
{
  "temp": "26℃",
  "weather": "晴",
  "humidity": "55%",
  "wind": "南风2级"
}
```
- 返回示例（失败）：
   json
{
  "temp": "---℃",
  "weather": "---",
  "humidity": "---%",
  "wind": "---",
  "error": "天气爬取失败: [具体错误信息]"
}

4.2 植物识别接口
- 接口路径：`/api/plant`
- 请求方式：`POST`
- 请求参数：表单参数`image`（值为图片的Base64编码字符串）
- 返回示例（识别成功）：
```json
{
  "plant_name": "向日葵",
  "confidence": 98.23
}
```
- 返回示例（识别失败）：
```json
{
  "plant_name": "向日葵",
  "confidence": 0.0,
  "error": "无识别结果"
}
```
