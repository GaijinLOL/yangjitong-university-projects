# -*- coding: utf-8 -*-
"""在官方训练集上微调 YOLO 模型（CPU 版，可复现）。

以现有 model/best.pt 为预训练权重（yolo11n，已具备同域特征），
在 dataset/（tools/prepare_dataset.py 生成）上继续微调。

用法（在项目根目录执行）：
    run_cpu.bat tools\\train_model.py --epochs 100 --batch 8 --name curtains_v2
    冒烟估时：--epochs 1 --name smoke

产物：
    runs/<name>/weights/best.pt   验证集最优权重
    runs/<name>/results.csv       逐 epoch 指标
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)                      # data.yaml 里 path: dataset 是相对根目录的
sys.path.insert(0, str(ROOT))       # 便携运行时不会自动把 cwd 加入 sys.path


def main():
    ap = argparse.ArgumentParser(description="官方训练集微调 YOLO（CPU）")
    ap.add_argument("--epochs", type=int, default=100, help="训练轮数")
    ap.add_argument("--batch", type=int, default=8, help="批大小（CPU 建议 4-8）")
    ap.add_argument("--imgsz", type=int, default=640, help="与推理保持一致，勿改小")
    ap.add_argument("--model", default="model/best.pt", help="预训练权重")
    ap.add_argument("--name", default="curtains_v2", help="训练名称（runs/<name>）")
    ap.add_argument("--patience", type=int, default=20, help="早停耐心")
    ap.add_argument("--close-mosaic", type=int, default=10, help="最后 N epoch 关闭 mosaic")
    ap.add_argument("--device", default="cpu", help="cpu（本机无 NVIDIA GPU）")
    ap.add_argument("--copy-paste", type=float, default=0.15, dest="copy_paste",
                    help="copy-paste 概率，针对稀有类（hole/断丝）")
    ap.add_argument("--resume", action="store_true",
                    help="从 runs/<name>/weights/last.pt 断点续训（epoch/优化器/学习率全恢复）")
    args = ap.parse_args()

    from ultralytics import YOLO

    if args.resume:
        model_path = str(ROOT / "runs" / args.name / "weights" / "last.pt")
        if not Path(model_path).is_file():
            print(f"找不到断点 {model_path}，无法续训", file=sys.stderr)
            sys.exit(1)
    else:
        model_path = str(ROOT / args.model)

    model = YOLO(model_path)
    model.train(
        data=str(ROOT / "dataset" / "data.yaml"),
        resume=args.resume,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        workers=2,
        cache="ram",                 # 170 张图全量进内存，消除磁盘 IO 瓶颈
        patience=args.patience,
        close_mosaic=args.close_mosaic,
        copy_paste=args.copy_paste,
        hsv_v=0.4,                   # 灰度图亮度扰动增强（光照波动）
        project=str(ROOT / "runs"),
        name=args.name,
        exist_ok=True,
        seed=42,                     # 可复现
        verbose=True,
    )
    print(f"训练完成，权重位于 runs/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
