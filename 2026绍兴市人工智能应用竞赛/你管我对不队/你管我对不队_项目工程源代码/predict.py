# -*- coding: utf-8 -*-
"""
Curtains3 表面缺陷检测 —— 推理入口（Python 模块 + 命令行）

现场设备无需安装 Python / YOLO 环境：直接用随包 runtime_cpu 里的 python.exe
运行本文件即可。GPU 加速需在系统 Python 中按 requirements-cuda.txt 安装。

用法示例（在交付包根目录执行）：
    run_cpu.bat  predict.py --source samples\gray_val_0003.png --json
    run_cuda.bat predict.py --source samples --save out --json
    run_cpu.bat  predict.py --source 0 --gray --camera        # 黑白工业相机实时预览

作为模块调用：
    from predict import CurtainsDetector
    det = CurtainsDetector()                 # 自动选择 CPU / CUDA
    results = det.predict_frame(gray_frame)  # gray_frame 可以是 HxW 单通道灰度
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = ROOT / "model" / "best.pt"

# 类别中文名，仅用于人机界面展示；类别顺序以 model.names 为准（本模型来自训练 data.yaml）
CLASS_NAME_ZH = {
    "hole": "孔洞",
    "ink": "墨水/污点",
    "broken_filament": "断丝",
}


# --------------------------------------------------------------------------- #
# 图像预处理：统一转成 3 通道 BGR uint8
# --------------------------------------------------------------------------- #
def to_bgr3(image, gray_bit_shift: int | None = None) -> np.ndarray:
    """把各种相机/文件输入统一成 3 通道 BGR uint8。

    关键点（黑白云台相机必读）：
      本模型训练集是「灰度内容存成三通道 PNG」，即 R=G=B 逐像素完全相等。
      因此单通道灰度图直接用 GRAY2BGR 复制三通道即可与训练分布完全对齐，
      无需伪彩色、无需 CLAHE 等额外处理。

    支持输入：
      - HxW    单通道灰度（uint8 直接复制；uint16 先降位深再复制）
      - HxWx1  单通道灰度
      - HxWx3  BGR（原样返回）
      - HxWx4  BGRA（丢弃 alpha）
    """
    import cv2

    if image is None:
        raise ValueError("输入图像为 None")

    arr = np.asarray(image)

    # 位深统一到 uint8
    if arr.dtype != np.uint8:
        if arr.dtype == np.uint16:
            shift = 8 if gray_bit_shift is None else int(gray_bit_shift)
            arr = np.clip(arr.astype(np.uint32) >> shift, 0, 255).astype(np.uint8)
        elif np.issubdtype(arr.dtype, np.floating):
            # 浮点输入按 min-max 拉伸（相机 SDK 直接给出归一化/浮点缓冲时）
            lo, hi = float(np.nanmin(arr)), float(np.nanmax(arr))
            arr = (np.zeros_like(arr, dtype=np.uint8) if hi <= lo
                   else ((arr - lo) * (255.0 / (hi - lo))).astype(np.uint8))
        else:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

    if arr.ndim == 2:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if arr.ndim == 3:
        c = arr.shape[2]
        if c == 1:
            return cv2.cvtColor(arr[:, :, 0], cv2.COLOR_GRAY2BGR)
        if c == 3:
            return np.ascontiguousarray(arr)
        if c == 4:
            return np.ascontiguousarray(arr[:, :, :3])
    raise ValueError(f"不支持的图像形状: {arr.shape}")


def is_gray_content(bgr: np.ndarray) -> bool:
    """判断三通道图是否为「灰度内容」（R=G=B）。"""
    if bgr.ndim != 3 or bgr.shape[2] < 3:
        return True
    return bool(np.array_equal(bgr[:, :, 0], bgr[:, :, 1]) and np.array_equal(bgr[:, :, 1], bgr[:, :, 2]))


# --------------------------------------------------------------------------- #
# 核心检测器
# --------------------------------------------------------------------------- #
class CurtainsDetector:
    """Curtains3 三分类缺陷检测器（hole / ink / broken_filament）。

    参数
    ----
    weights : 权重路径，默认 <包根>/model/best.pt
    device  : "auto"(默认) | "cpu" | "cuda" | "cuda:0" | 0
    conf    : 置信度阈值，默认 0.37
    iou     : NMS IoU 阈值，默认 0.7（与训练一致）
    imgsz   : 推理分辨率，默认 640（与训练一致，不要随意改小）
    max_det : 单图最大检出数，默认 300（与训练一致）
    half    : GPU fp16 推理；None 表示有 CUDA 时自动开启，CPU 上强制关闭
    """

    def __init__(self, weights=None, device="auto", conf=0.37, iou=0.7,
                 imgsz=640, max_det=300, half=None, warmup=False, verbose=False,
                 slice_inference=False, slice_size=640, slice_overlap=0.20,
                 fusion_iou=0.55):
        if weights is None:
            weights = str(DEFAULT_WEIGHTS)
        weights = str(weights)
        if not Path(weights).is_file():
            raise FileNotFoundError(f"找不到权重文件: {weights}")

        import torch
        from ultralytics import YOLO

        self.device = self._resolve_device(device)
        self.conf = float(conf)
        self.iou = float(iou)
        self.imgsz = int(imgsz)
        self.max_det = int(max_det)
        self.half = bool(torch.cuda.is_available()) if half is None else bool(half)
        if self.device == "cpu":
            self.half = False
        self.verbose = bool(verbose)
        self.slice_inference = bool(slice_inference)
        self.slice_size = max(64, int(slice_size))
        self.slice_overlap = min(0.8, max(0.0, float(slice_overlap)))
        self.fusion_iou = min(0.95, max(0.05, float(fusion_iou)))

        self.model = YOLO(weights)
        self.model.to(self.device)
        # 类别名以权重内为准
        self.names = {int(k): str(v) for k, v in dict(self.model.names).items()}

        self._kw = dict(imgsz=self.imgsz, conf=self.conf, iou=self.iou,
                        max_det=self.max_det, half=self.half, device=self.device,
                        verbose=False)
        if warmup:
            self.warmup()

    # ---------------- 设备 ----------------
    @staticmethod
    def _resolve_device(device) -> str:
        import torch
        if device in (None, "auto"):
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        if device in ("cuda", "gpu"):
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "指定了 CUDA 设备，但当前环境检测不到可用的 NVIDIA GPU。\n"
                    "请改用 --device cpu，或确认已安装匹配的显卡驱动。")
            return "cuda:0"
        if device == "cpu":
            return "cpu"
        if isinstance(device, int):
            return f"cuda:{device}"
        s = str(device)
        if s.isdigit():
            return f"cuda:{s}"
        if s.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(f"指定了 {s}，但检测不到可用的 NVIDIA GPU。")
        return s

    def info(self) -> dict:
        import torch
        return {
            "weights": str(self.model.ckpt_path) if getattr(self, "model", None) else "",
            "task": "detect",
            "classes": self.names,
            "classes_zh": {k: CLASS_NAME_ZH.get(v, v) for k, v in self.names.items()},
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_name": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else None),
            "torch": torch.__version__,
            "ultralytics": __import__("ultralytics").__version__,
            "imgsz": self.imgsz,
            "conf": self.conf,
            "iou": self.iou,
            "max_det": self.max_det,
            "half": self.half,
            "slice_inference": self.slice_inference,
            "slice_size": self.slice_size,
            "slice_overlap": self.slice_overlap,
            "fusion_iou": self.fusion_iou,
        }

    def warmup(self, rounds: int = 2):
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(rounds):
            self.model.predict(dummy, **self._kw)
        return self

    # ---------------- 推理 ----------------
    @staticmethod
    def _iou(a, b):
        ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
        ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
        ab = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
        return inter / max(aa + ab - inter, 1e-9)

    def _fuse_detections(self, raw, h, w):
        """按类别做 confidence 加权框融合，消除切片边界重复框。"""
        fused = []
        for cid in sorted({int(d["class_id"]) for d in raw}):
            pending = sorted((d for d in raw if int(d["class_id"]) == cid),
                             key=lambda d: float(d["conf"]), reverse=True)
            while pending and len(fused) < self.max_det:
                seed = pending.pop(0)
                group = [seed]
                remain = []
                for d in pending:
                    if self._iou(seed["xyxy"], d["xyxy"]) >= self.fusion_iou:
                        group.append(d)
                    else:
                        remain.append(d)
                pending = remain
                weights = np.array([max(float(d["conf"]), 1e-6) for d in group])
                boxes = np.array([d["xyxy"] for d in group], dtype=float)
                box = (boxes * weights[:, None]).sum(axis=0) / weights.sum()
                best = max(group, key=lambda d: float(d["conf"]))
                fused.append({"class_id": cid, "class_name": best["class_name"],
                              "class_name_zh": best["class_name_zh"],
                              "conf": round(max(float(d["conf"]) for d in group), 4),
                              "xyxy": box.tolist()})
        fused.sort(key=lambda d: float(d["conf"]), reverse=True)
        for d in fused:
            x1, y1, x2, y2 = d["xyxy"]
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            d["xyxy"] = [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
            d["xywhn"] = [round((x1+x2)/(2*w), 6), round((y1+y2)/(2*h), 6),
                           round((x2-x1)/w, 6), round((y2-y1)/h, 6)]
            d["area_px"] = int(round((x2-x1)*(y2-y1)))
        return fused[:self.max_det]

    def predict_frame(self, image, save_path=None, gray_bit_shift=None,
                      slice_inference=None) -> dict:
        """【前端主要接口】单帧推理。

        image 可以是：HxW 灰度 ndarray / HxWx3 BGR ndarray / 图像文件路径 / bytes。
        返回 dict：{"detections": [...], "infer_ms": float, "shape": [h, w]}
        """
        import cv2

        if isinstance(image, (str, os.PathLike)):
            raw = cv2.imread(str(image), cv2.IMREAD_UNCHANGED)
            if raw is None:
                raise FileNotFoundError(f"无法读取图像: {image}")
        elif isinstance(image, (bytes, bytearray)):
            buf = np.frombuffer(image, dtype=np.uint8)
            raw = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
            if raw is None:
                raise ValueError("无法解码传入的图像字节流")
        else:
            raw = image

        bgr = to_bgr3(raw, gray_bit_shift=gray_bit_shift)
        h, w = bgr.shape[:2]

        use_slices = self.slice_inference if slice_inference is None else bool(slice_inference)
        t0 = time.perf_counter()
        jobs = [(bgr, 0, 0)]
        if use_slices and (w > self.slice_size or h > self.slice_size):
            step = max(1, int(self.slice_size * (1.0 - self.slice_overlap)))
            xs = list(range(0, max(1, w - self.slice_size + 1), step))
            ys = list(range(0, max(1, h - self.slice_size + 1), step))
            if xs[-1] != max(0, w - self.slice_size): xs.append(max(0, w - self.slice_size))
            if ys[-1] != max(0, h - self.slice_size): ys.append(max(0, h - self.slice_size))
            jobs = [(bgr[y:y+self.slice_size, x:x+self.slice_size], x, y) for y in ys for x in xs]
        raw = []
        for tile, ox, oy in jobs:
            res = self.model.predict(tile, **self._kw)[0]
            boxes = res.boxes
            if boxes is None or len(boxes) == 0: continue
            xyxy = boxes.xyxy.detach().cpu().numpy()
            cls = boxes.cls.detach().cpu().numpy().astype(int)
            cfs = boxes.conf.detach().cpu().numpy()
            for i in np.argsort(-cfs):
                if float(cfs[i]) < self.conf: continue
                x1,y1,x2,y2 = xyxy[i] + np.array([ox,oy,ox,oy])
                cid = int(cls[i])
                raw.append({"class_id": cid, "class_name": self.names.get(cid, str(cid)),
                            "class_name_zh": CLASS_NAME_ZH.get(self.names.get(cid, ""), self.names.get(cid, "")),
                            "conf": float(cfs[i]), "xyxy": [float(x1),float(y1),float(x2),float(y2)]})
        infer_ms = (time.perf_counter() - t0) * 1000.0
        dets = self._fuse_detections(raw, h, w)

        out = {
            "detections": dets,
            "num": len(dets),
            "infer_ms": round(infer_ms, 2),
            "shape": [h, w],
            "device": self.device,
            "sliced": bool(use_slices and len(jobs) > 1),
            "tiles": len(jobs),
        }
        if save_path is not None:
            out["saved"] = self.save_visual(bgr, dets, save_path)
        return out

    def predict_batch(self, images, **kw):
        """批量推理，返回 list，顺序与输入一致。"""
        return [self.predict_frame(im, **kw) for im in images]

    # ---------------- 可视化 ----------------
    def save_visual(self, image_bgr: np.ndarray, detections, save_path) -> str:
        import cv2
        vis = self.draw(image_bgr, detections)
        p = Path(save_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(p.suffix or ".jpg", vis)
        if not ok:
            raise RuntimeError("结果图编码失败")
        buf.tofile(str(p))
        return str(p)

    def draw(self, image_bgr, detections):
        """在图像上画框（就地返回新图，不改原图）。"""
        import cv2
        vis = image_bgr.copy()
        # 缺陷类别配色（BGR）
        colors = {0: (0, 0, 255), 1: (0, 200, 255), 2: (255, 120, 0)}
        for d in detections:
            x1, y1, x2, y2 = (int(round(v)) for v in d["xyxy"])
            cid = int(d["class_id"])
            color = colors.get(cid, (0, 255, 0))
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"{d['class_name']} {d['conf']:.2f}"
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            ty = max(y1 - 4, th + 4)
            cv2.rectangle(vis, (x1, ty - th - 4), (x1 + tw + 4, ty + base - 2), color, -1)
            cv2.putText(vis, label, (x1 + 2, ty - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 255, 255) if sum(color) < 400 else (0, 0, 0), 1, cv2.LINE_AA)
        return vis

    # ---------------- 相机流 ----------------
    def run_camera(self, index=0, gray=True, show=True, limit=0, save_dir=None,
                   width=None, height=None, gray_bit_shift=None, quiet=False):
        """打开黑白工业相机（或 UVC 摄像头）做实时检测。

        gray=True 时会尝试让相机直接输出单通道（Mono8），拿到的帧交给
        predict_frame，内部用 GRAY2BGR 复制三通道，与训练分布对齐。
        """
        import cv2

        cap = cv2.VideoCapture(int(index), cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(int(index))          # 退回厂商 SDK / 默认后端
        if not cap.isOpened():
            raise RuntimeError(f"无法打开相机 index={index}。"
                               "若使用厂商 SDK（海康/大恒/Basler 等），请先用 SDK 取帧，"
                               "再把单通道 ndarray 传给 predict_frame()。")
        if width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        if height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        if gray:
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)        # 请求原始单通道输出
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        n, t_all, stat = 0, 0.0, {}
        saved = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                r = self.predict_frame(frame, gray_bit_shift=gray_bit_shift)
                n += 1
                t_all += r["infer_ms"]
                for d in r["detections"]:
                    stat[d["class_name"]] = stat.get(d["class_name"], 0) + 1
                if save_dir and r["num"] > 0:
                    sv = Path(save_dir) / f"{int(time.time() * 1000)}.jpg"
                    self.save_visual(to_bgr3(frame, gray_bit_shift), r["detections"], sv)
                    saved += 1
                if show:
                    vis = self.draw(to_bgr3(frame, gray_bit_shift), r["detections"])
                    cv2.putText(vis, f"{r['infer_ms']:.1f} ms  {r['num']} def",
                                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow("Curtains3 defect detect", vis)
                    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                        break
                if not quiet and n % 30 == 0:
                    print(f"[camera] frames={n} avg={t_all / n:.1f}ms")
                if limit and n >= limit:
                    break
        finally:
            cap.release()
            if show:
                cv2.destroyAllWindows()
        return {"frames": n, "avg_infer_ms": round(t_all / n, 2) if n else 0,
                "class_counts": stat, "saved": saved}

    # ---------------- 性能 ----------------
    def benchmark(self, rounds=20, shape=(512, 512)) -> dict:
        dummy = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
        self.model.predict(dummy, **self._kw)                 # 预热
        t0 = time.perf_counter()
        for _ in range(rounds):
            self.model.predict(dummy, **self._kw)
        ms = (time.perf_counter() - t0) / rounds * 1000
        return {"rounds": rounds, "input": f"{shape[1]}x{shape[0]}",
                "avg_infer_ms": round(ms, 2), "fps": round(1000.0 / ms, 1),
                "device": self.device, "half": self.half}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov"}


def _expand_sources(src: str):
    p = Path(src)
    if p.is_dir():
        return sorted([q for q in p.iterdir() if q.suffix.lower() in IMAGE_EXT])
    return [p]


def _selfcheck(weights) -> int:
    print("=" * 62)
    print("Curtains3 部署包自检")
    print("=" * 62)
    try:
        import sys as _sys
        import torch
        from ultralytics import YOLO
        import cv2
        import numpy as _np
        print(f"[1/5] Python      : {_sys.version.split()[0]}  ({_sys.executable})")
        print(f"      numpy/cv2   : {_np.__version__} / {cv2.__version__}")
        print(f"[2/5] torch       : {torch.__version__}   cuda_available={torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"      GPU         : {torch.cuda.get_device_name(0)}  (CUDA {torch.version.cuda})")
        else:
            print("      GPU         : 无（将使用 CPU 推理）")
        print(f"[3/5] ultralytics : {__import__('ultralytics').__version__}")
    except Exception as e:                                    # noqa: BLE001
        print(f"[!] 依赖导入失败: {e}")
        return 1

    w = Path(weights)
    if not w.is_file():
        print(f"[4/5] 权重        : 缺失 -> {w}")
        return 1
    import hashlib
    h = hashlib.sha256()
    with open(w, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(f"[4/5] 权重        : {w.name}  {w.stat().st_size:,} bytes")
    print(f"      sha256      : {h.hexdigest()}")

    try:
        det = CurtainsDetector(weights=w)
        print(f"[5/5] 模型加载    : OK   类别={det.names}  设备={det.device}")
        r = det.predict_frame(np.zeros((512, 512), dtype=np.uint8))
        print(f"      空帧推理    : {r['infer_ms']} ms  (detections={r['num']})")
        b = det.benchmark(rounds=10)
        print(f"      性能        : {b['avg_infer_ms']} ms/帧  ≈ {b['fps']} FPS  ({b['device']})")
    except Exception as e:                                    # noqa: BLE001
        print(f"[!] 推理失败: {e}")
        return 1
    print("=" * 62)
    print("[OK] 自检通过")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="Curtains3 表面缺陷检测推理（hole / ink / broken_filament）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  run_cpu.bat  predict.py --source samples\\gray_val_0003.png --json\n"
               "  run_cuda.bat predict.py --source samples --save out --json\n"
               "  run_cpu.bat  predict.py --source 0 --camera --gray\n"
               "  run_cpu.bat  predict.py --selfcheck\n")
    ap.add_argument("--source", help="图片/文件夹/视频路径，或相机序号（配合 --camera）")
    ap.add_argument("--weights", default=str(DEFAULT_WEIGHTS), help="权重路径，默认 model/best.pt")
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda | cuda:0 | 0")
    ap.add_argument("--conf", type=float, default=0.37, help="置信度阈值，默认 0.37")
    ap.add_argument("--iou", type=float, default=0.7, help="NMS IoU，默认 0.7")
    ap.add_argument("--imgsz", type=int, default=640, help="推理分辨率，默认 640")
    ap.add_argument("--max-det", type=int, default=300, dest="max_det", help="单图最大检出数")
    ap.add_argument("--slice", action="store_true", dest="slice_inference",
                    help="启用重叠切片推理并做加权框融合（大图/小缺陷推荐）")
    ap.add_argument("--slice-size", type=int, default=640,
                    help="切片边长，默认 640")
    ap.add_argument("--slice-overlap", type=float, default=0.20,
                    help="切片重叠比例 0~0.8，默认 0.20")
    ap.add_argument("--fusion-iou", type=float, default=0.55,
                    help="融合框 IoU 阈值，默认 0.55")
    ap.add_argument("--half", action="store_true", help="强制 fp16（仅 CUDA 有效）")
    ap.add_argument("--save", metavar="OUTDIR", help="保存可视化结果到目录")
    ap.add_argument("--json", action="store_true", help="把结果以 JSON 输出到 stdout")
    ap.add_argument("--json-out", metavar="FILE", help="把结果写入 JSON 文件（UTF-8）")
    ap.add_argument("--gray", action="store_true", help="按单通道灰度读取（黑白相机）")
    ap.add_argument("--gray-bit-shift", type=int, default=None,
                    help="uint16 灰度降位深右移位数，默认 8（即 /256）")
    ap.add_argument("--camera", action="store_true", help="按相机实时模式运行")
    ap.add_argument("--no-show", action="store_true", help="相机模式下不弹窗")
    ap.add_argument("--limit", type=int, default=0, help="相机模式最多处理帧数，0=不限")
    ap.add_argument("--width", type=int, default=None, help="相机采集宽度")
    ap.add_argument("--height", type=int, default=None, help="相机采集高度")
    ap.add_argument("--benchmark", type=int, metavar="N", default=0, help="跑 N 次性能测试")
    ap.add_argument("--warmup", action="store_true", default=True, help="启动时预热（默认开）")
    ap.add_argument("--no-warmup", action="store_false", dest="warmup", help="关闭预热")
    ap.add_argument("--selfcheck", action="store_true", help="环境与模型自检")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.selfcheck:
        return _selfcheck(args.weights)

    if not args.source:
        build_parser().print_help()
        return 2

    det = CurtainsDetector(weights=args.weights, device=args.device, conf=args.conf,
                           iou=args.iou, imgsz=args.imgsz, max_det=args.max_det,
                           half=(True if args.half else None), warmup=args.warmup,
                           slice_inference=args.slice_inference, slice_size=args.slice_size,
                           slice_overlap=args.slice_overlap, fusion_iou=args.fusion_iou)

    if args.camera:
        r = det.run_camera(index=args.source, gray=args.gray, show=not args.no_show,
                           limit=args.limit, save_dir=args.save, width=args.width,
                           height=args.height, gray_bit_shift=args.gray_bit_shift)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    if args.benchmark:
        print(json.dumps(det.benchmark(rounds=args.benchmark), ensure_ascii=False, indent=2))

    sources = _expand_sources(args.source)
    if not sources:
        print(f"未找到可处理的图像: {args.source}", file=sys.stderr)
        return 2

    all_out = {}
    for p in sources:
        if p.suffix.lower() in VIDEO_EXT:
            print(f"跳过视频（请用 --camera 或自行逐帧调用）: {p}", file=sys.stderr)
            continue
        save_path = None
        if args.save:
            save_path = Path(args.save) / f"{p.stem}_pred{p.suffix}"
        try:
            r = det.predict_frame(p, save_path=save_path, gray_bit_shift=args.gray_bit_shift)
        except Exception as e:                                # noqa: BLE001
            print(f"[!] {p.name}: {e}", file=sys.stderr)
            continue
        all_out[str(p)] = r
        if not args.json:
            head = ", ".join(f"{d['class_name']}({d['conf']:.2f})" for d in r["detections"]) or "无检出"
            print(f"{p.name}: {r['num']} 个目标 | {r['infer_ms']} ms | {head}")

    payload = {"device": det.device, "weights": args.weights, "results": all_out}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
        if not args.json:
            print(f"JSON 结果已写入: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
