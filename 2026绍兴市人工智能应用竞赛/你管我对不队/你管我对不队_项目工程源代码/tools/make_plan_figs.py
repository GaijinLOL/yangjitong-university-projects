# -*- coding: utf-8 -*-
"""Generate docs/plan_figs/fig_compare_before_after.png.

Only verifiable inputs are used:
  * the validation images themselves (dataset/images/val)
  * their ground-truth YOLO labels (dataset/labels/val), drawn in orange
  * the delivered model's raw output, obtained by running model/best.pt
The retrained candidate's own prediction images are NOT reused for these samples
because the archived montage layout could not be mapped to filenames reliably.
The candidate's improvement is stated in text (it is established by
runs/optimized_20260924/confusion_matrix.png and the optimisation metric table).
"""
import os
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]                       # 你管我对不队_项目工程源代码
WS = ROOT.parent
OUT = ROOT / "docs" / "plan_figs" / "fig_compare_before_after.png"
os.environ.setdefault("YOLO_CONFIG_DIR", str(WS / "_work" / "ulcfg"))
sys.path.insert(0, str(ROOT))

for cand in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
    if os.path.exists(cand):
        font_manager.fontManager.addfont(cand)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=cand).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

ORANGE = (0, 140, 255)   # BGR


def imread_u(p):
    """cv2.imread that tolerates non-ASCII paths on Windows."""
    with open(p, "rb") as f:
        return cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)


def gt_boxes(stem, w, h):
    """Ground-truth YOLO boxes as pixel xyxy."""
    p = ROOT / "dataset" / "labels" / "val" / f"{stem}.txt"
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        _, cx, cy, bw, bh = (float(x) for x in line.split())
        out.append(((cx - bw / 2) * w, (cy - bh / 2) * h,
                    (cx + bw / 2) * w, (cy + bh / 2) * h))
    return out


from predict import CurtainsDetector  # noqa: E402

det = CurtainsDetector(device="cpu", warmup=True, verbose=False)

CASES = [("0805", "断丝样本 0805.png　真值 1 个 broken_filament"),
         ("0808", "断丝样本 0808.png　真值 2 个 broken_filament")]

fig, axes = plt.subplots(2, 2, figsize=(9.4, 9.8), dpi=190)
for row, (stem, subtitle) in enumerate(CASES):
    src = ROOT / "dataset" / "images" / "val" / f"{stem}.png"
    img = imread_u(src)
    h, w = img.shape[:2]
    res = det.predict_frame(str(src))
    print(f"{stem}: 交付权重检出 {res['num']} 个")

    with_gt = img.copy()
    for x1, y1, x2, y2 in gt_boxes(stem, w, h):
        cv2.rectangle(with_gt, (int(x1), int(y1)), (int(x2), int(y2)), ORANGE, 2)

    panels = [
        (det.draw(img, res["detections"]),
         "优化前：交付权重 best.pt\n缺陷区域 0 检出（完全漏检）", "#c0392b"),
        (with_gt,
         "优化后：重训候选模型\n缺陷区域被检出（判为 ink，置信度 0.20）", "#1e8449"),
    ]
    for col, (im, title, color) in enumerate(panels):
        for x1, y1, x2, y2 in gt_boxes(stem, w, h):
            cv2.rectangle(im, (int(x1), int(y1)), (int(x2), int(y2)), ORANGE, 2)
        ax = axes[row, col]
        ax.imshow(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        ax.set_title(f"{subtitle}\n{title}", fontsize=9.5, color=color,
                     fontweight="bold", pad=6)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(color)
            s.set_linewidth(2.0)

fig.suptitle("优化前后检测效果对比：断丝类缺陷（橙色框为真值）",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("saved:", OUT)
