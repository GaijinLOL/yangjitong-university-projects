"""本地可视化应用服务：复用既有推理模块，不修改模型逻辑。

路由：
    POST /api/predict         单图/单帧推理（multipart 上传；可选表单字段
                              gray=1 把彩色帧转单通道灰度，供实时摄像头模式
                              对齐训练分布使用）
    GET  /api/config          服务端配置（团队名）
    其他 GET                   静态页面（frontend/）
"""
from __future__ import annotations

import argparse
import cgi
import json
import os
import sys
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 便携运行时可能无法写入用户配置目录，统一落到包内可写目录。
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))
os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(ROOT / ".ultralytics"))
sys.path.insert(0, str(ROOT))
from config.classes import (  # noqa: E402
    ALLOWED_IMAGE_EXTENSIONS, CLASS_NAME_ZH, MODEL_CLASS_TO_STANDARD, TEAM_NAME,
)

DETECTOR = None


def get_detector():
    """延迟加载模型，服务启动后保持单例，避免每次请求重复加载权重。"""
    global DETECTOR
    if DETECTOR is None:
        from predict import CurtainsDetector
        DETECTOR = CurtainsDetector(device="auto", conf=0.37, warmup=True)
    return DETECTOR


def normalize_detection(item: dict) -> dict:
    """只向页面暴露原图绝对像素坐标与规范英文类别名。"""
    standard = MODEL_CLASS_TO_STANDARD.get(item["class_name"], item["class_name"])
    if standard not in CLASS_NAME_ZH:
        raise ValueError(f"模型输出了未配置的类别：{standard}")
    x1, y1, x2, y2 = item["xyxy"]
    return {
        "class_name": standard,
        "class_name_zh": CLASS_NAME_ZH[standard],
        "confidence": round(float(item["conf"]), 2),
        "x_min": round(float(x1), 2), "y_min": round(float(y1), 2),
        "x_max": round(float(x2), 2), "y_max": round(float(y2), 2),
    }


class AppHandler(SimpleHTTPRequestHandler):
    """静态页面 + 推理 JSON 接口。"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "frontend"), **kwargs)

    def log_message(self, format, *args):
        print("[web] " + format % args)

    def end_headers(self):
        # 静态资源与接口一律禁止缓存，避免前端改版后浏览器仍加载旧 JS/CSS
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------------- GET ----------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(HTTPStatus.OK, {"team_name": TEAM_NAME})
            return
        super().do_GET()

    # ---------------- POST ----------------
    def do_POST(self):
        try:
            if self.path == "/api/predict":
                self.handle_predict()
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"detail": "接口不存在"})
        except Exception as exc:  # 将后端异常转为页面可读提示，不泄露堆栈。
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": str(exc)})

    def handle_predict(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST"})
        upload = form["image"] if "image" in form else None
        if upload is None or not upload.filename:
            raise ValueError("请选择一张图片")
        filename = Path(upload.filename).name
        if Path(filename).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError("仅支持 jpg、jpeg、png、bmp 图片")
        image = upload.file.read()
        # 实时摄像头模式（gray=1）：浏览器摄像头输出彩色帧，而模型训练集是
        # 「灰度内容存成三通道 PNG」。这里先转单通道灰度，predict_frame 内部
        # 会用 GRAY2BGR 复制三通道，与训练分布完全对齐。
        gray_field = form["gray"] if "gray" in form else None
        if gray_field is not None and str(gray_field.value) in ("1", "true", "True"):
            import cv2
            import numpy as np
            buf = np.frombuffer(image, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("无法解码摄像头帧")
            image = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        slice_field = form["slice"] if "slice" in form else None
        use_slice = (slice_field is not None and
                     str(slice_field.value) in ("1", "true", "True"))
        result = get_detector().predict_frame(image, slice_inference=use_slice)
        detections = [normalize_detection(item) for item in result["detections"]
                      if float(item["conf"]) >= 0.37]
        self.send_json(HTTPStatus.OK, {
            "image_id": filename, "detections": detections,
            "defect_count": len(detections), "status": "NG" if detections else "OK",
            "inference_time_ms": result["infer_ms"], "shape": result["shape"],
            "sliced": result.get("sliced", False), "tiles": result.get("tiles", 1),
        })


def main():
    parser = argparse.ArgumentParser(description="工业视觉质检可视化服务")
    parser.add_argument("--port", type=int, default=8080, help="网页服务端口")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), AppHandler)
    print(f"可视化应用已启动：http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
