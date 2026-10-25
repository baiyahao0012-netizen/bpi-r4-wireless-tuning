# -*- coding: utf-8 -*-
"""重画方法对比图：去掉'方法一/二/三'代号，用直白方案名"""
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

# 从上到下的顺序（与原图一致）
rows = [
    ("跨频隔离（EF 后）", 42.00, True),
    ("AC 策略 2.4G 同型号", 51.30, True),
    ("AC 策略 5G 慢 STA", 0.71, False),
    ("AC 策略 5G 快 STA", 2.07, True),
    ("airtime 权重 慢 STA", 0.77, False),
    ("airtime 权重 快 STA", 1.14, False),
    ("FQ 加权 配置 4:1", 1.02, False),
]
labels = [r[0] for r in rows][::-1]
vals = [r[1] for r in rows][::-1]
colors = ["#3E5C76" if r[2] else "#A25B5B" for r in rows][::-1]

fig, ax = plt.subplots(figsize=(10, 4.8))
y = np.arange(len(labels))
bars = ax.barh(y, vals, color=colors, height=0.6)
for b, v in zip(bars, vals):
    ax.text(v + 0.8, b.get_y() + b.get_height()/2, f"{v:.2f}", va="center", fontsize=10)
ax.axvline(1.0, color="#646A73", ls="--", lw=1)
ax.text(1.05, len(labels)-0.4, "1:1 无效果", fontsize=9, color="#646A73")
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10)
ax.set_xscale("log")
ax.set_xlim(0.5, 100)
ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50, 100])
ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
ax.set_xlabel("VIP : 普通 吞吐比（对数刻度）", fontsize=11)
ax.set_title("各方案 VIP 吞吐比对比（>2 为有效，蓝色有效 / 红色无效）", fontsize=13)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="x", ls="--", alpha=0.35)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "method_summary.png"), dpi=150, facecolor="white")
print("redrawn method_summary")
