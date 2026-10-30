# -*- coding: utf-8 -*-
"""一键打包部署包（交给别人的干净 zip）。

用法（在工程根目录执行）：
    runtime_cpu\\python.exe tools\\pack_deploy.py                 # 打包到上层目录
    runtime_cpu\\python.exe tools\\pack_deploy.py --dry-run       # 只列清单，不打包
    runtime_cpu\\python.exe tools\\pack_deploy.py --with-dataset  # 附带训练数据集（约 +68 MB）
    runtime_cpu\\python.exe tools\\pack_deploy.py --no-runtime    # 不含便携运行时（省约 0.75 GB）
"""
from __future__ import annotations

import argparse
import hashlib
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM = "你管我对不队"

# 默认排除的开发残留 / 可再生成产物（目录名，任意层级命中即剪枝）
EXCLUDE_DIRS = {".git", "__pycache__", "runs", "outputs", ".ultralytics"}
# 默认排除的根目录散文件（运行时产物）
EXCLUDE_FILES = {"你管我对不队_检测结果.csv", "SHA256SUMS.txt"}

# SHA256SUMS.txt 记录的关键文件（相对路径，反斜杠风格，与 gen_checksums.py 一致）
KEY_FILES = [
    "README.md", "predict.py",
    "backend\\__init__.py", "backend\\csv_export.py", "backend\\verify_demo.py",
    "backend\\web_server.py",
    "config\\__init__.py", "config\\classes.py",
    "examples\\demo_module_api.py",
    "frontend\\index.html",
    "frontend\\src\\camera.js",
    "frontend\\src\\api.js", "frontend\\src\\exporter.js",
    "frontend\\src\\main.js", "frontend\\src\\renderer.js",
    "frontend\\styles\\app.css", "frontend\\styles\\overrides.css",
    "model\\best.pt",
    "requirements\\requirements-common.txt", "requirements\\requirements-cpu.txt",
    "requirements\\requirements-cuda.txt",
    "runtime_cpu\\python.exe",
    "runtime_cpu\\Lib\\site-packages\\torch\\_C.cp311-win_amd64.pyd",
    "run_cpu.bat", "run_cuda.bat", "start_web.bat",
    "samples\\test_0007.png", "samples\\val_0011.png",
    "samples\\val_0011_pred.jpg", "samples\\val_0013.png",
    "先读我.txt", "前端对接文档.md", "部署说明.md",
]


def iter_files(with_dataset: bool, no_runtime: bool):
    """遍历待打包文件（Path 对象）。"""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = Path(dirpath).relative_to(ROOT)
        parts = rel.parts
        if any(p in EXCLUDE_DIRS for p in parts):
            dirnames[:] = []
            continue
        if parts:
            top = parts[0]
            if top == "dataset" and not with_dataset:
                dirnames[:] = []
                continue
            if top == "runtime_cpu" and no_runtime:
                dirnames[:] = []
                continue
        for fn in filenames:
            if not parts and fn in EXCLUDE_FILES:
                continue
            yield Path(dirpath) / fn


def fmt_mb(n: float) -> str:
    return f"{n / 1048576:.1f} MB"


def main() -> None:
    ap = argparse.ArgumentParser(description="打包 Curtains3 部署包")
    ap.add_argument("--dry-run", action="store_true", help="只列清单，不打包")
    ap.add_argument("--with-dataset", action="store_true",
                    help="附带 dataset/ 训练数据集")
    ap.add_argument("--no-runtime", action="store_true",
                    help="不含 runtime_cpu/ 便携运行时")
    ap.add_argument("--out", default=None, help="输出目录（默认工程上层目录）")
    args = ap.parse_args()

    files = sorted(iter_files(args.with_dataset, args.no_runtime))
    total = sum(f.stat().st_size for f in files)
    print(f"待打包: {len(files)} 个文件, 共 {fmt_mb(total)}")
    print(f"  数据集 dataset/      : {'包含' if args.with_dataset else '排除'} "
          f"(--with-dataset 可包含)")
    print(f"  便携运行时 runtime_cpu/: {'排除' if args.no_runtime else '包含'} "
          f"(--no-runtime 可排除)")
    print(f"  始终排除: {', '.join(sorted(EXCLUDE_DIRS))} 及检测结果 CSV")

    if args.dry_run:
        print("\n-- 清单（前 60 项）--")
        for f in files[:60]:
            print("  ", f.relative_to(ROOT).as_posix())
        if len(files) > 60:
            print(f"  ... 其余 {len(files) - 60} 项省略")
        return

    out_dir = Path(args.out) if args.out else ROOT.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / f"{TEAM}_部署包.zip"

    sums = [
        "# Curtains3 缺陷检测部署包 - SHA256 校验值",
        f"# 生成时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "# 校验方式(Windows): certutil -hashfile <相对路径> SHA256",
        "",
    ]

    t0 = time.time()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for i, f in enumerate(files, 1):
            rel = f.relative_to(ROOT).as_posix()
            z.write(f, rel)
            rel_win = rel.replace("/", "\\")
            if rel_win in KEY_FILES:
                sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel_win}")
            if i % 500 == 0:
                print(f"  ... {i}/{len(files)}  ({time.time() - t0:.0f}s)")
        z.writestr("SHA256SUMS.txt", "\n".join(sums) + "\n")

    dt = time.time() - t0
    print(f"完成: {out_zip}  ({fmt_mb(os.path.getsize(out_zip))}, 用时 {dt:.0f}s)")
    print(f"包内 SHA256SUMS.txt 记录 {len(sums) - 4} 个关键文件")
    print("交接步骤: 把 zip 发给对方 -> 解压到全英文路径 -> 让对方跑 "
          "run_cpu.bat predict.py --selfcheck（详见 部署说明.md 第 4 节）")


if __name__ == "__main__":
    main()
