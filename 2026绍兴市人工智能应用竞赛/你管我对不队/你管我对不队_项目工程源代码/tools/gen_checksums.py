# -*- coding: utf-8 -*-
"""交付包 SHA256 校验文件生成器。

用法（在交付包根目录执行）：
    run_cpu.bat tools\\gen_checksums.py

输出：覆盖根目录 SHA256SUMS.txt，格式与官方要求一致：
    <sha256>  <相对路径>     （哈希后两个空格，反斜杠路径，UTF-8 编码）

校验方式（Windows）：
    certutil -hashfile <相对路径> SHA256
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---- 交付包固定源码清单（按目录分组，缺失文件会报错提示） ----
FILES = [
    # 根目录
    "predict.py",
    "run_cpu.bat", "run_cuda.bat", "start_web.bat",
    "README.md", "先读我.txt", "前端对接文档.md", "部署说明.md",
    # 后端
    "backend/__init__.py", "backend/web_server.py",
    "backend/csv_export.py", "backend/verify_demo.py",
    # 配置
    "config/__init__.py", "config/classes.py",
    # 示例
    "examples/demo_module_api.py",
    # 前端
    "frontend/index.html",
    "frontend/src/camera.js", "frontend/src/api.js", "frontend/src/exporter.js",
    "frontend/src/main.js", "frontend/src/renderer.js",
    "frontend/styles/app.css", "frontend/styles/overrides.css",
    # 模型权重
    "model/best.pt",
    # 依赖清单
    "requirements/requirements-common.txt",
    "requirements/requirements-cpu.txt",
    "requirements/requirements-cuda.txt",
]

# 随包便携运行时关键二进制（体积大，只校验入口与 torch 核心，保证运行时完整性）
RUNTIME_KEYS = [
    "runtime_cpu/python.exe",
    "runtime_cpu/Lib/site-packages/torch/_C.cp311-win_amd64.pyd",
]

# samples 目录下全部样例图片（动态收集，新增样例自动纳入）
SAMPLE_DIR = ROOT / "samples"
SAMPLE_EXT = {".png", ".jpg", ".jpeg", ".bmp"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> list[tuple[str, str]]:
    """返回 [(相对路径(反斜杠), 哈希), ...]，按路径排序。"""
    entries, missing = [], []
    for rel in FILES + RUNTIME_KEYS:
        p = ROOT / rel.replace("\\", "/")
        if not p.is_file():
            missing.append(rel)
            continue
        entries.append((rel.replace("/", "\\"), sha256(p)))
    for p in sorted(SAMPLE_DIR.iterdir()):
        if p.suffix.lower() in SAMPLE_EXT and p.is_file():
            rel = f"samples\\{p.name}"
            entries.append((rel, sha256(p)))
    if missing:
        print("以下清单文件不存在，请核对：", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)
    return sorted(entries)


def main():
    entries = collect()
    lines = [
        "# Curtains3 缺陷检测部署包 - SHA256 校验值",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# 校验方式(Windows): certutil -hashfile <相对路径> SHA256",
        "",
    ]
    lines += [f"{h}  {rel}" for rel, h in entries]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 SHA256SUMS.txt，共 {len(entries)} 个条目。")


if __name__ == "__main__":
    main()
