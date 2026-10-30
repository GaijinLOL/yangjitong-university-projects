# -*- coding: utf-8 -*-
"""在验证集上扫描 YOLO 置信度阈值，寻找部署阈值。

示例（项目根目录）：
    run_cpu.bat tools\\scan_conf_threshold.py
    run_cpu.bat tools\\scan_conf_threshold.py --start 0.10 --stop 0.80 --step 0.05

输出：runs/conf_scan.csv，并打印按 F1 最优的阈值及当前基准 0.37 的指标。
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))


def main():
    ap = argparse.ArgumentParser(description="扫描 YOLO 验证集置信度阈值")
    ap.add_argument("--weights", default="model/best.pt")
    ap.add_argument("--data", default="dataset/data.yaml")
    ap.add_argument("--start", type=float, default=0.10)
    ap.add_argument("--stop", type=float, default=0.80)
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default="runs/conf_scan.csv")
    ap.add_argument("--baseline", type=float, default=0.37)
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(str(ROOT / args.weights))
    thresholds = []
    x = args.start
    while x <= args.stop + 1e-9:
        thresholds.append(round(x, 4))
        x += args.step
    # 无论步长如何，都强制纳入当前部署基准，避免只取最近网格点。
    if args.start <= args.baseline <= args.stop and all(abs(t - args.baseline) > 1e-9 for t in thresholds):
        thresholds.append(round(args.baseline, 4))
        thresholds.sort()

    rows = []
    for conf in thresholds:
        metrics = model.val(data=str(ROOT / args.data), split="val", imgsz=args.imgsz,
                            batch=8, device=args.device, workers=0, conf=conf,
                            plots=False, verbose=False)
        p = float(metrics.box.mp)
        r = float(metrics.box.mr)
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        row = {"conf": conf, "precision": p, "recall": r,
               "f1": f1, "map50": float(metrics.box.map50),
               "map50_95": float(metrics.box.map)}
        rows.append(row)
        print("conf={conf:.2f}  P={precision:.4f}  R={recall:.4f}  F1={f1:.4f}  "
              "mAP50={map50:.4f}  mAP50-95={map50_95:.4f}".format(**row))

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    best = max(rows, key=lambda row: row["f1"])
    baseline = min(rows, key=lambda row: abs(row["conf"] - args.baseline))
    print(f"\\n推荐阈值（验证集 F1 最优）: {best['conf']:.2f}")
    print("依据: P={precision:.4f}, R={recall:.4f}, F1={f1:.4f}, "
          "mAP50={map50:.4f}, mAP50-95={map50_95:.4f}".format(**best))
    print("当前基准 {conf:.2f}: P={precision:.4f}, R={recall:.4f}, F1={f1:.4f}".format(**baseline))
    print(f"扫描明细已保存: {out}")


if __name__ == "__main__":
    main()
