# -*- coding: utf-8 -*-
"""官方训练集 -> ultralytics 标准数据集（分层划分 8:2 + data.yaml）。

数据按四组分层（保证稀有类别 hole/broken_filament 在验证集中有代表）：
    ink 组  0001-0120（120 张，主要是 ink）
    hole 组 0597-0605（9 张，hole 全部样本）
    ok 组   0640-0670（31 张，无缺陷 OK）
    bf 组   0801-0810（10 张，broken_filament 全部样本）

用法（在项目根目录）：
    run_cpu.bat tools\\prepare_dataset.py
    run_cpu.bat tools\\prepare_dataset.py --src D:\\赛题数据集\\训练集

输出：
    dataset/images/train|val/*.png
    dataset/labels/train|val/*.txt
    dataset/data.yaml
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 原始赛题训练集目录。为避免在提交材料中硬编码主办方信息，
# 默认读取环境变量 CURTAIN_SRC，未设置时回退到本工程 dataset/ 已生成的数据。
SRC = Path(os.environ.get("CURTAIN_SRC", ROOT / "dataset" / "_src"))
DST = ROOT / "dataset"
VAL_RATIO = 0.2
SEED = 42

GROUPS = {
    "ink":  [f"{i:04d}" for i in range(1, 121)],        # 0001-0120
    "hole": [f"{i:04d}" for i in range(597, 606)],      # 0597-0605
    "ok":   [f"{i:04d}" for i in range(640, 671)],      # 0640-0670
    "bf":   [f"{i:04d}" for i in range(801, 811)],      # 0801-0810
}


def main():
    ap = argparse.ArgumentParser(description="划分官方训练集为 ultralytics 数据集")
    ap.add_argument("--src", default=str(SRC),
                    help="原始赛题训练集目录（也可用环境变量 CURTAIN_SRC 指定）")
    args = ap.parse_args()
    src = Path(args.src)

    if not src.is_dir():
        print(f"[错误] 找不到原始训练集目录：{src}\n"
              f"       请用 --src 指定，或设置环境变量 CURTAIN_SRC。", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(SEED)
    splits = {"train": [], "val": []}
    for group, stems in GROUPS.items():
        missing = [s for s in stems if not (src / f"{s}.png").is_file()]
        if missing:
            print(f"[错误] {group} 组缺图: {missing}", file=sys.stderr)
            sys.exit(1)
        n_val = max(1, round(len(stems) * VAL_RATIO))
        val = sorted(rng.sample(stems, n_val))
        for s in stems:
            splits["val" if s in val else "train"].append(s)
        print(f"  {group}: {len(stems)} 张 -> train {len(stems) - n_val} / val {n_val}")

    if DST.exists():
        shutil.rmtree(DST)
    for part in ("train", "val"):
        for sub in ("images", "labels"):
            (DST / sub / part).mkdir(parents=True, exist_ok=True)

    for part in ("train", "val"):
        for s in splits[part]:
            shutil.copy2(src / f"{s}.png", DST / "images" / part / f"{s}.png")
            shutil.copy2(src / f"{s}.txt", DST / "labels" / part / f"{s}.txt")

    (DST / "data.yaml").write_text(
        "# 由 tools/prepare_dataset.py 自动生成（随机种子 42，可复现）\n"
        "path: dataset\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 3\n"
        "names: ['hole', 'ink', 'broken_filament']\n",
        encoding="utf-8",
    )

    # 校验输出：统计 train/val 各类框数
    print("划分完成：")
    for part in ("train", "val"):
        n_img = len(list((DST / "images" / part).glob("*.png")))
        cls_count = {0: 0, 1: 0, 2: 0}
        for t in (DST / "labels" / part).glob("*.txt"):
            for line in t.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    cls_count[int(float(line.split()[0]))] += 1
        print(f"  {part}: {n_img} 张图 | hole={cls_count[0]} ink={cls_count[1]} broken_filament={cls_count[2]}")


if __name__ == "__main__":
    main()
