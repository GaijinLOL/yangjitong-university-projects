# -*- coding: utf-8 -*-
"""
Curtains3 缺陷检测 —— Python 模块调用最小示例

在交付包根目录执行：
    run_cpu.bat  examples\demo_module_api.py
    run_cuda.bat examples\demo_module_api.py

本文件演示三件事：
  1. 直接把「单通道灰度帧」(ndarray) 交给检测器 —— 对应黑白工业相机
  2. 检测单个图片文件并从返回值里读取结构化结果
  3. 如何接入厂商相机 SDK（海康 / 大恒 / Basler 等）的取帧回调
"""
import sys
from pathlib import Path

import numpy as np

# 让脚本无论从哪个目录启动都能 import 到包根的 predict.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from predict import CurtainsDetector, to_bgr3  # noqa: E402


def demo_gray_frame(det: CurtainsDetector):
    """【最重要】模拟黑白相机送进来的单通道灰度帧。"""
    print("\n--- 示例 1：单通道灰度帧（黑白相机主路径）---")

    # 现场实际情况：gray 由相机 SDK 直接给出，形状 (H, W)，dtype=uint8
    # 这里用一张样例图转成灰度来模拟
    import cv2
    bgr = cv2.imread(str(ROOT / "samples" / "val_0013.png"))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    print(f"送入帧: shape={gray.shape}, dtype={gray.dtype}  (单通道，未做任何处理)")

    result = det.predict_frame(gray)          # 内部自动 GRAY2BGR 复制三通道
    print(f"检出 {result['num']} 个目标，耗时 {result['infer_ms']} ms")
    for d in result["detections"]:
        print(f"  - {d['class_name']}({d['class_name_zh']}) conf={d['conf']} "
              f"xyxy={d['xyxy']} area={d['area_px']}px")
    return result


def demo_gray_uint16(det: CurtainsDetector):
    """16 位灰度相机（Mono12/Mono16）的处理方式。"""
    print("\n--- 示例 2：16 位灰度帧 ---")
    rng = np.random.default_rng(0)
    frame16 = (rng.random((512, 512)) * 65535).astype(np.uint16)   # shape (H, W), uint16
    # 默认右移 8 位（等价 /256）映射到 8bit；若现场是 12bit 有效数据，可传 gray_bit_shift=4
    r = det.predict_frame(frame16, gray_bit_shift=8)
    print(f"uint16 帧处理成功，检出 {r['num']} 个目标（随机噪声图，预期无真实缺陷）")


def demo_image_file(det: CurtainsDetector):
    """检测图片文件。"""
    print("\n--- 示例 3：图片文件 ---")
    p = ROOT / "samples" / "val_0011.png"
    r = det.predict_frame(p, save_path=ROOT / "samples" / "val_0011_pred.jpg")
    print(f"{p.name}: {r['num']} 个目标，{r['infer_ms']} ms")
    print("结果图已保存: samples/val_0011_pred.jpg")
    return r


def demo_vendor_camera(det: CurtainsDetector):
    """接入厂商相机 SDK 的写法（以伪代码说明，各厂商 API 名称不同）。"""
    print("\n--- 示例 4：厂商相机 SDK 接入写法（伪代码，未实际执行）---")
    code = '''
    # 1) 用厂商 SDK 打开相机，设置为 Mono8（单通道 8bit）
    #    海康: MvCamera / 大恒: GxIAPI / Basler: pylon
    cam = VendorSdk.open_camera(serial="xxxx", pixel_format="Mono8")
    cam.start_grabbing()

    det = CurtainsDetector(device="auto")        # 进程内只创建一次，不要每帧创建

    while running:
        frame = cam.get_frame()                  # 返回 numpy (H, W) uint8 单通道
        result = det.predict_frame(frame)         # 单帧推理
        if result["num"] > 0:
            on_defect_found(result["detections"]) # 你的业务逻辑：报警 / 打标 / 存图
        else:
            on_pass()

    cam.stop_grabbing(); cam.close()
    '''
    print(code)


if __name__ == "__main__":
    print("=" * 64)
    det = CurtainsDetector(device="auto", conf=0.37)
    print("运行环境:", det.info()["device"], "| 类别:", det.names)
    print("=" * 64)

    demo_gray_frame(det)
    demo_gray_uint16(det)
    demo_image_file(det)
    demo_vendor_camera(det)

    print("\n全部示例执行完毕。")
