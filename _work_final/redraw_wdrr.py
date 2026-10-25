# -*- coding: utf-8 -*-
"""重画 wdrr_ratio.png：去掉箭头与文字重叠"""
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

fig, ax = plt.subplots(figsize=(9, 5))
labels = ["配置权重\nfq_weight BE:VO", "实测吞吐比\nBE:VO"]
vals = [4.0, 1.02]
colors = ["#3E6EA8", "#A25B5B"]
bars = ax.bar(labels, vals, color=colors, width=0.45)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.12, f"{v:.2f} : 1", ha="center", fontsize=14, fontweight="bold")
ax.set_ylabel("BE : VO 比值", fontsize=12)
ax.set_ylim(0, 5)
ax.set_yticks([0, 1, 2, 3, 4])
ax.set_title("WDRR per-AC 加权：配置 4:1 权重，实测吞吐仍约 1:1", fontsize=14)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "wdrr_ratio.png"), dpi=150, facecolor="white")
print("redrawn wdrr_ratio")
