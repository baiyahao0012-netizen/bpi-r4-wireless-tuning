# -*- coding: utf-8 -*-
"""文档一 3.1.3 两张图重画：随机图=纯散点去离群；排序图=平滑曲线；图内不烧示意小字"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        fm.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

OUT = r"D:\Desktop\AI 辅助对话\draft_be2590bd_folder\charts"

# 同一组 50 个样本（与之前一致），去掉 max=884.6 离群点，剩 49 个
rng = np.random.default_rng(42)
samples = rng.lognormal(mean=np.log(220.3), sigma=0.334, size=50)
samples = np.clip(samples, 147.2, 884.6)
srt = np.sort(samples)
srt[0] = 147.2
srt[24] = 220.3
srt[47] = 381.5
srt[48] = 430.0
srt = np.delete(srt, 49)          # 删掉 max=884.6
n = len(srt)

# 随机顺序
rng2 = np.random.default_rng(7)
rand_order = rng2.permutation(n)
samples_random = srt[rand_order]

INK = "#1F2329"; GRAY = "#646A73"; BLUE = "#3E5C76"

# ---------- 图2：随机顺序散点（不连线） ----------
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.scatter(range(1, n+1), samples_random, color=BLUE, s=22, zorder=3)
ax.axhline(220.3, color=GRAY, ls="--", lw=1)
ax.text(n+0.5, 220.3, "p50 = 220.3 μs", va="center", fontsize=9, color=GRAY)
ax.set_xlabel("测量序号（按发生顺序）", fontsize=11)
ax.set_ylabel("下发时延（μs）", fontsize=11)
ax.set_title("EDCA 下发时延（空载）：按测量顺序的样本分布", fontsize=13)
ax.set_xlim(0, n+6); ax.set_ylim(100, 500)
ax.grid(ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "edca_random.png"), dpi=150, facecolor="white")
plt.close(fig)

# ---------- 图3：排序后平滑曲线 ----------
xs = np.arange(1, n+1)
# 三次样条平滑
try:
    from scipy.interpolate import make_interp_spline
    xs_smooth = np.linspace(1, n, 300)
    spl = make_interp_spline(xs, srt, k=3)
    ys_smooth = spl(xs_smooth)
except ImportError:
    xs_smooth = xs; ys_smooth = srt

fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(xs_smooth, ys_smooth, color=BLUE, lw=1.8, zorder=3)
ax.scatter(xs, srt, color=BLUE, s=10, zorder=4)
ax.axhline(220.3, color=GRAY, ls="--", lw=1)
ax.axhline(381.5, color=GRAY, ls=":", lw=1)
ax.annotate("p50 = 220.3 μs", xy=(25, 220.3), xytext=(10, 300), fontsize=9, color=GRAY,
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.8))
ax.annotate("p95 = 381.5 μs", xy=(47, 381.5), xytext=(32, 440), fontsize=9, color=GRAY,
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.8))
ax.set_xlabel("排序后序号（从小到大）", fontsize=11)
ax.set_ylabel("下发时延（μs）", fontsize=11)
ax.set_title("同一组样本按时延升序排列：百分位在此读出", fontsize=13)
ax.set_xlim(0, n+2); ax.set_ylim(100, 500)
ax.grid(ls="--", alpha=0.35)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "edca_sorted.png"), dpi=150, facecolor="white")
plt.close(fig)

print("done: n =", n)
