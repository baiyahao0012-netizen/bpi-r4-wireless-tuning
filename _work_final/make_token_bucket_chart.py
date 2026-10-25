# -*- coding: utf-8 -*-
"""A+ token bucket 原型实测：比值 + 总吞吐双子图"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        fm.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

OUT = r"D:\Desktop\AI 辅助对话\draft_db2abcf0_folder\charts"
os.makedirs(OUT, exist_ok=True)

labels = ["QUANTUM=512\n权重 4:1", "QUANTUM=32\n权重 4:1", "QUANTUM=32\n权重 8:2"]
ratio = [1.45, 3.47, 1.70]
throughput = [np.nan, 27, 40]   # 第一组总吞吐未单独记录
BLUE = "#3E5C76"; GRAY = "#9AA3AD"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))

b1 = ax1.bar(labels, ratio, color=BLUE, width=0.55)
for b, v in zip(b1, ratio):
    ax1.text(b.get_x()+b.get_width()/2, v+0.06, f"{v:.2f}:1", ha="center", fontsize=11, fontweight="bold")
ax1.axhline(4.0, color=GRAY, ls="--", lw=1)
ax1.text(2.45, 4.05, "目标 4:1", fontsize=9, color=GRAY, ha="right")
ax1.set_ylim(0, 4.6)
ax1.set_ylabel("实测 VIP : 普通 比值", fontsize=11)
ax1.set_title("(a) 实测比值", fontsize=12)
ax1.grid(axis="y", ls="--", alpha=0.35)
ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

vals = [0 if np.isnan(t) else t for t in throughput]
colors = [GRAY if np.isnan(t) else BLUE for t in throughput]
b2 = ax2.bar(labels, vals, color=colors, width=0.55)
for b, v, raw in zip(b2, vals, throughput):
    txt = "未记录" if np.isnan(raw) else f"{int(raw)} Mbit/s"
    ax2.text(b.get_x()+b.get_width()/2, v+1, txt, ha="center", fontsize=10, color=GRAY if np.isnan(raw) else "#1F2329")
ax2.set_ylim(0, 55)
ax2.set_ylabel("总吞吐（Mbit/s）", fontsize=11)
ax2.set_title("(b) 总吞吐（QUANTUM 过小即崩溃）", fontsize=12)
ax2.grid(axis="y", ls="--", alpha=0.35)
ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

fig.suptitle("A+ token bucket 原型（mt76 per-WCID）：帧粒度门控下，比值与总吞吐不可兼得", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "token_bucket.png"), dpi=150, facecolor="white")
print("saved token_bucket.png")
