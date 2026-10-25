# -*- coding: utf-8 -*-
"""重画4张图：标题简洁，去掉条件描述和箭头标注"""
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

D1 = r"D:\Desktop\AI 辅助对话\draft_be2590bd_folder\charts"
D3 = r"D:\Desktop\AI 辅助对话\draft_db2abcf0_folder\charts"

# 1. wdrr_ratio.png（文档3）
fig, ax = plt.subplots(figsize=(8, 4.5))
labels = ["配置权重\nfq_weight BE:VO", "实测吞吐比\nBE:VO"]
vals = [4.0, 1.02]
colors = ["#3E6EA8", "#A25B5B"]
bars = ax.bar(labels, vals, color=colors, width=0.45)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.12, f"{v:.2f} : 1", ha="center", fontsize=14, fontweight="bold")
ax.set_ylabel("BE : VO 比值", fontsize=12)
ax.set_ylim(0, 5)
ax.set_yticks([0, 1, 2, 3, 4])
ax.set_title("BE : VO 吞吐比", fontsize=14)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(D3, "wdrr_ratio.png"), dpi=150, facecolor="white")
plt.close()

# 2. edca_random.png（文档1）—— 用原数据（49个点）
np.random.seed(42)
# 还原大致分布：均值220，偏正态
lat = np.array([178,297,220,302,220,191,274,149,244,224,166,270,382,322,269,241,254,216,176,284,27,283,159,265,227,150,430,193,207,212,205,296,295,168,168,258,250,201,251,277,231,238,166,158,252,226,286,186,229])
x = np.arange(len(lat))
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.scatter(x, lat, color="#3E5C76", s=35, zorder=3)
ax.axhline(220.3, color="#646A73", ls="--", lw=1, zorder=2)
ax.text(len(lat)-1, 225, "p50 = 220 μs", fontsize=10, color="#646A73", ha="right")
ax.set_ylabel("下发时延（μs）", fontsize=12)
ax.set_xlabel("测量序号", fontsize=12)
ax.set_ylim(100, 500)
ax.set_title("EDCA 下发时延", fontsize=14)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(D1, "edca_random.png"), dpi=150, facecolor="white")
plt.close()

# 3. edca_sorted.png
lat_sorted = np.sort(lat)
x2 = np.arange(len(lat_sorted))
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(x2, lat_sorted, color="#3E5C76", marker="o", markersize=4, lw=1.5)
ax.axhline(220.3, color="#646A73", ls="--", lw=1)
ax.axhline(381.5, color="#646A73", ls=":", lw=1)
ax.text(len(lat_sorted)-1, 225, "p50 = 220 μs", fontsize=10, color="#646A73", ha="right")
ax.text(len(lat_sorted)-1, 386, "p95 = 382 μs", fontsize=10, color="#646A73", ha="right")
ax.set_ylabel("下发时延（μs）", fontsize=12)
ax.set_xlabel("排序后序号", fontsize=12)
ax.set_ylim(100, 500)
ax.set_title("EDCA 下发时延（升序）", fontsize=14)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(D1, "edca_sorted.png"), dpi=150, facecolor="white")
plt.close()

# 4. ampdu_throughput.png
fig, ax = plt.subplots(figsize=(9, 4.5))
labels4 = ["cap=0\n默认窗口", "cap=2\n窗口≤2 MPDU", "cap=0\n写回恢复"]
vals4 = [381.0, 74.3, 402.0]
colors4 = ["#3E5C76", "#A25B5B", "#3E5C76"]
bars4 = ax.bar(labels4, vals4, color=colors4, width=0.5)
for b, v in zip(bars4, vals4):
    ax.text(b.get_x()+b.get_width()/2, v+8, f"{v:.1f}", ha="center", fontsize=12, fontweight="bold")
ax.set_ylabel("下行吞吐（Mbit/s）", fontsize=12)
ax.set_ylim(0, 460)
ax.set_title("A-MPDU 聚合窗口对吞吐的影响", fontsize=14)
ax.grid(axis="y", ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(D1, "ampdu_throughput.png"), dpi=150, facecolor="white")
plt.close()

print("all redrawn")
