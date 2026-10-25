# -*- coding: utf-8 -*-
"""A+ nft policer：目标比值 vs 实测比值"""
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

groups = ["2:1\n(普通限 12 MB/s)", "4:1\n(普通限 9 MB/s)", "4:1 参考\n(普通限 6 MB/s)"]
target = [2.0, 4.0, 4.0]
actual = [2.13, 3.69, 6.06]

x = np.arange(len(groups))
w = 0.35
fig, ax = plt.subplots(figsize=(8.5, 4.2))
b1 = ax.bar(x - w/2, target, w, color="#9AA3AD", label="目标比值")
b2 = ax.bar(x + w/2, actual, w, color="#3E5C76", label="实测比值")
for b, v in zip(b1, target):
    ax.text(b.get_x()+b.get_width()/2, v+0.08, f"{v:.2f}", ha="center", fontsize=10, color="#646A73")
for b, v in zip(b2, actual):
    ax.text(b.get_x()+b.get_width()/2, v+0.08, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold", color="#1F2329")
ax.set_xticks(x); ax.set_xticklabels(groups)
ax.set_ylabel("VIP : 普通 吞吐比", fontsize=11)
ax.set_ylim(0, 7)
ax.set_title("A+ 交付方案（nft policer）：目标比值与实测比值（10 s 双流，3 轮均值）", fontsize=13)
ax.legend(frameon=False)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "aplus_ratio.png"), dpi=150, facecolor="white")
print("saved aplus_ratio.png")
