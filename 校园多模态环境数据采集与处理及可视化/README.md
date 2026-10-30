# 校园多模态环境数据采集与处理及可视化

项目目录 `CJ1/` 是一个小型数据应用：后端采集天气和植物识别结果，前端通过接口展示环境信息、图片识别结果和图表。

## 数据分析视角

- 采集：天气网页抓取、图片上传和第三方识别接口调用；
- 处理：统一字段、处理缺失结果、保存 MongoDB 记录；
- 服务：Flask API 将数据提供给前端；
- 展示：HTML、CSS、JavaScript 和图表组件完成可视化交付。

## 主要目录

- `CJ1/backend/`：Flask 服务、天气采集和植物识别接口；
- `CJ1/frontend/`：页面、接口调用和图表展示；
- `CJ1/测试数据/`：演示用图片；
- `CJ1/requirements.txt`：Python 依赖；
- `CJ1/.env.example`：配置模板，不包含真实密钥。

## 本地运行

```powershell
cd CJ1
pip install -r requirements.txt
python backend/app.py
```

默认服务端口为 `5000`。如果需要使用百度 AI 植物识别，请复制 `.env.example`，并在本机设置 `BAIDU_APP_ID`、`BAIDU_API_KEY`、`BAIDU_SECRET_KEY`；这些值不要提交到 Git。

完整说明和接口示例见 [`CJ1/README.md`](./CJ1/README.md)。

