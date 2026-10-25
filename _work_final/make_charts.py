# -*- coding: utf-8 -*-
"""生成 BPI-R4 两份汇报飞书文档所需的全部图表 PNG"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch

# 中文字体
for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        fm.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

OUT = r"D:\Desktop\AI 辅助对话\_work_final\charts"
os.makedirs(OUT, exist_ok=True)

C1 = "#2F6FB6"   # 主蓝
C2 = "#E8A33D"   # 橙
C3 = "#7BA05B"   # 绿
C4 = "#B05555"   # 红棕
GRAY = "#555555"

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)

# ---------- 1. EDCA 三场景时延统计 ----------
fig, ax = plt.subplots(figsize=(9, 5))
scenes = ["空载连续切换\n(n=50)", "20 s 打流中切换\n(n=15)", "三流并发打流中\n(n=30)"]
mins = [147.2, 235.8, 170.7]
p50 = [220.3, 300.7, 341.8]
p95 = [381.5, 550.5, 562.4]
maxs = [884.6, 689.0, 1064.9]
x = np.arange(3)
w = 0.18
for i, (data, color, label) in enumerate(zip(
        [mins, p50, p95, maxs], [C3, C1, C2, C4],
        ["min", "p50", "p95", "max"])):
    bars = ax.bar(x + (i - 1.5) * w, data, w, label=label, color=color)
    for b, v in zip(bars, data):
        ax.text(b.get_x() + b.get_width() / 2, v + 15, f"{v:.0f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(scenes, fontsize=11)
ax.set_ylabel("时延 (μs)", fontsize=12)
ax.set_ylim(0, 1250)
ax.set_title("EDCA 命令→固件 ACK 时延（三个场景的 min/p50/p95/max）", fontsize=13, pad=12)
ax.legend(ncol=4, fontsize=10, frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
save(fig, "edca_latency_stats.png")

# ---------- 2. EDCA 时延分布示意（重建，标注示意） ----------
rng = np.random.default_rng(42)
mu, sigma = np.log(220.3), 0.334
samples = np.clip(rng.lognormal(mu, sigma, 50), 120, 900)
samples.sort()
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
axes[0].scatter(range(1, 51), samples, s=28, color=C1, alpha=0.8)
axes[0].set_title("(a) 按测量顺序：随机波动", fontsize=12)
axes[0].set_xlabel("测量序号", fontsize=11); axes[0].set_ylabel("时延 (μs)", fontsize=11)
axes[1].plot(np.sort(samples), color=C2, lw=2, marker="o", ms=4)
axes[1].set_title("(b) 按时延大小排序：单调上升曲线", fontsize=12)
axes[1].set_xlabel("排序位置", fontsize=11)
for ax_ in axes:
    ax_.spines["top"].set_visible(False); ax_.spines["right"].set_visible(False)
    ax_.grid(axis="y", linestyle="--", alpha=0.4)
fig.suptitle("示意：EDCA 时延分布（原始逐条已随板端重启丢失，按 min/p50/p95/max 统计特征重建）",
             fontsize=11, y=1.02)
save(fig, "edca_distribution_demo.png")

# ---------- 3. A-MPDU 吞吐三态 ----------
fig, ax = plt.subplots(figsize=(8, 4.6))
states = ["cap=0（默认）", "cap=2（≤2 MPDU）", "cap=0（恢复）"]
vals = [381, 74.3, 402]
colors = [C3, C4, C2]
bars = ax.bar(states, vals, width=0.55, color=colors)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.1f} Mbit/s", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("下行吞吐 (Mbit/s)", fontsize=12)
ax.set_ylim(0, 480)
ax.set_title("A-MPDU 聚合窗口实时修改：吞吐 402 → 74.3 → 402 Mbit/s", fontsize=13, pad=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.annotate("−81.5%", xy=(1, 74.3), xytext=(1, 150), ha="center", fontsize=12, color=C4,
            arrowprops=dict(arrowstyle="->", color=C4))
save(fig, "ampdu_throughput.png")

# ---------- 4. A-MPDU 生效时间线 ----------
fig, ax = plt.subplots(figsize=(11, 3.4))
points = [
    ("t=0\n写 agg_win_cap=2", 0),
    ("+11.5 ms\nwrite 返回\n（3 STA BA 重放）", 11.5),
    ("+0~0.5 s\nWLAN5 首降", 500),
    ("+2.5 s\nWLAN3 开始降", 2500),
    ("+3.0 s\n进入新稳态", 3000),
    ("+8 s\n写回 cap=0", 8000),
    ("+11.5 s\n恢复（约 3.5 s）", 11500),
]
xs = [p[1] for p in points]
ax.set_xscale("symlog", linthresh=1)
ax.set_xlim(-50, 20000)
ax.axhline(0, color=GRAY, lw=1.2)
for x_, label in points:
    ax.plot([x_], [0], "o", color=C1, ms=7, zorder=5)
    ax.annotate(label, xy=(x_, 0), xytext=(x_, 0.45), ha="center", fontsize=9.5,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
seg_colors = [C1, C1, C4, C4, C2, C2]
for i in range(len(points) - 1):
    ax.axvspan(max(xs[i], -50), xs[i + 1], alpha=0.08, color=seg_colors[i])
ax.set_yticks([])
ax.set_title("A-MPDU：命令毫秒级下发（10.5–11.5 ms），业务秒级收敛（0.5–3 s，恢复 3.5 s）", fontsize=12, pad=10)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="x", labelsize=9)
ax.set_xticks([0, 11.5, 500, 2500, 3000, 8000, 11500])
ax.set_xticklabels(["0", "11.5 ms", "0.5 s", "2.5 s", "3 s", "8 s", "11.5 s"])
save(fig, "ampdu_timeline.png")

# ---------- 5. MCS 结果 ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
labels = ["force_mcs=0", "force_mcs=1", "force_mcs=255\n(自动)"]
tx = [864.8, 960.7, 1020]
thr = [348, 342, 387]
axes[0].bar(labels, tx, width=0.55, color=[C4, C4, C3])
for i, v in enumerate(tx):
    axes[0].text(i, v + 15, f"{v:.0f}", ha="center", fontsize=10)
axes[0].set_title("station tx bitrate (Mbit/s)\nHE-MCS8 / HE-MCS9 —— 未锁到 MCS0/1", fontsize=11)
axes[0].set_ylim(0, 1150)
axes[1].bar(labels, thr, width=0.55, color=[C4, C4, C3])
for i, v in enumerate(thr):
    axes[1].text(i, v + 8, f"{v:.0f}", ha="center", fontsize=10)
axes[1].set_title("下行吞吐 (Mbit/s)\n348 / 342 —— 未随锁定值变化", fontsize=11)
axes[1].set_ylim(0, 480)
for ax_ in axes:
    ax_.spines["top"].set_visible(False); ax_.spines["right"].set_visible(False)
    ax_.grid(axis="y", linestyle="--", alpha=0.4)
fig.suptitle("MCS 锁定尝试：命令可下发（6.2–6.8 μs 内存写），但 AP 下行速率不生效（固件 RC）",
             fontsize=12, y=1.04)
save(fig, "mcs_results.png")

# ---------- 6. VO/BK 原始 100 ms 时间序列 ----------
data = []
with open(r"D:\Desktop\AI 辅助对话\_work_final\ac_mix_final.csv", encoding="utf-8") as f:
    f.readline()
    for line in f:
        parts = line.strip().split(",")
        if len(parts) >= 3:
            data.append((float(parts[0]), float(parts[1]), float(parts[2])))
t = [d[0] for d in data]; vo = [d[1] for d in data]; bk = [d[2] for d in data]
fig, ax = plt.subplots(figsize=(11, 4.4))
ax.plot(t, vo, color=C1, lw=1.0, label="VO 流", alpha=0.9)
ax.plot(t, bk, color=C2, lw=1.0, label="BK 流", alpha=0.9)
for s in (6, 12):
    ax.axvline(s, color=GRAY, ls="--", lw=1)
ax.text(3, 235, "默认 EDCA\n(VO 主导)", ha="center", fontsize=9, color=GRAY)
ax.text(9, 235, "VO 激进\n(BK 已饿死)", ha="center", fontsize=9, color=GRAY)
ax.text(16, 235, "VO/BK 参数对调\n(BK 主导)", ha="center", fontsize=9, color=GRAY)
ax.set_xlabel("时间 (s)", fontsize=11); ax.set_ylabel("吞吐 (Mbit/s)", fontsize=11)
ax.set_xlim(0, 20); ax.set_ylim(0, 260)
ax.set_title("VO/BK 混合 AC 竞争：原始 100 ms 分桶时序（真实逐桶数据，n=219）", fontsize=13, pad=10)
ax.legend(fontsize=10, frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
save(fig, "ac_mix_raw.png")

# ---------- 7. VO/BK 排序图 ----------
vo_sorted = sorted(vo)
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(range(1, len(vo_sorted) + 1), vo_sorted, color=C2, lw=2)
ax.set_xlabel("按吞吐大小排序的位置", fontsize=11)
ax.set_ylabel("VO 吞吐 (Mbit/s)", fontsize=11)
ax.set_title("VO 流 219 个分桶按吞吐大小排序：阶梯状分布", fontsize=13, pad=10)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
save(fig, "ac_mix_sorted.png")

# ---------- 8. 三阶段均值 ----------
fig, ax = plt.subplots(figsize=(9, 4.6))
phases = ["0–6 s\n默认 EDCA", "6–12 s\nVO 激进", "12–20 s\nBK 激进"]
vo_mean = [88.3, 96.9, 2.0]
bk_mean = [2.4, 2.4, 218.2]
x = np.arange(3); w = 0.32
ax.bar(x - w / 2, vo_mean, w, label="VO 平均", color=C1)
ax.bar(x + w / 2, bk_mean, w, label="BK 平均", color=C2)
for i in range(3):
    ax.text(x[i] - w / 2, vo_mean[i] + 6, f"{vo_mean[i]:.1f}", ha="center", fontsize=10)
    ax.text(x[i] + w / 2, bk_mean[i] + 6, f"{bk_mean[i]:.1f}", ha="center", fontsize=10)
    ratio = "36.2:1" if i == 0 else ("40.8:1" if i == 1 else "1:109")
    ax.text(x[i], 245, ratio, ha="center", fontsize=12, fontweight="bold", color=C4)
ax.set_xticks(x); ax.set_xticklabels(phases, fontsize=10)
ax.set_ylabel("吞吐 (Mbit/s)", fontsize=12); ax.set_ylim(0, 275)
ax.set_title("VO/BK 三阶段均值：EDCA 参数对调使 VO:BK 从 36:1 翻转到 1:109", fontsize=13, pad=10)
ax.legend(fontsize=10, frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
save(fig, "ac_mix_phases.png")

# ---------- 9. 12 s 切换逐桶细节 ----------
fig, ax = plt.subplots(figsize=(9, 4.4))
buckets = ["12.0–12.1 s", "12.1–12.2 s", "12.2–12.3 s", "12.3–12.4 s"]
v = [113.4, 46.7, 0.0, 0.0]
b = [0.2, 94.6, 175.8, 244.3]
x = np.arange(4); w = 0.32
ax.bar(x - w / 2, v, w, label="VO", color=C1)
ax.bar(x + w / 2, b, w, label="BK", color=C2)
for i in range(4):
    ax.text(x[i] - w / 2, v[i] + 6, f"{v[i]:.1f}", ha="center", fontsize=10)
    ax.text(x[i] + w / 2, b[i] + 6, f"{b[i]:.1f}", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(buckets, fontsize=10)
ax.set_ylabel("吞吐 (Mbit/s)", fontsize=12); ax.set_ylim(0, 280)
ax.set_title("12 s 处 VO/BK 参数对调：业务可见变化 0.1–0.2 s，0.2–0.3 s 进入新稳态", fontsize=12, pad=10)
ax.legend(fontsize=10, frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
save(fig, "ac_switch_detail.png")

# ---------- 10. WDRR 预期 vs 实测 ----------
fig, ax = plt.subplots(figsize=(8, 4.4))
cats = ["配置权重\nfq_weight BE:VO", "实测吞吐比\nBE:VO"]
vals = [4, 1.02]
bars = ax.bar(cats, vals, width=0.45, color=[C1, C4])
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.2f} : 1", ha="center", fontsize=12, fontweight="bold")
ax.set_ylim(0, 4.6)
ax.set_title("WDRR per-AC 加权：配置 4:1 权重，实测吞吐仍约 1:1", fontsize=13, pad=10)
ax.set_ylabel("BE : VO 比值", fontsize=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.annotate("fq 层是 per-flow 调度，AC 在 txq 层，\nper-AC 权重互相抵消", xy=(1, 1.02), xytext=(0.35, 3.2),
            fontsize=10, color=GRAY, arrowprops=dict(arrowstyle="->", color=GRAY))
save(fig, "wdrr_ratio.png")

# ---------- 11. airtime_weight (ATF) ----------
fig, ax = plt.subplots(figsize=(9, 4.4))
groups = ["VIP 在慢 STA\n(1024 vs 64)", "VIP 在快 STA\n(1024 vs 64)"]
vip = [140, 174]
norm = [183, 152]
x = np.arange(2); w = 0.32
ax.bar(x - w / 2, vip, w, label="VIP STA", color=C1)
ax.bar(x + w / 2, norm, w, label="普通 STA", color=C2)
for i in range(2):
    ax.text(x[i] - w / 2, vip[i] + 5, f"{vip[i]}", ha="center", fontsize=11)
    ax.text(x[i] + w / 2, norm[i] + 5, f"{norm[i]}", ha="center", fontsize=11)
ax.text(0, 205, "VIP 反而更慢\n(0.77×)", ha="center", fontsize=10, color=C4)
ax.text(1, 205, "仅 +14.5%", ha="center", fontsize=10, color=C4)
ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=10)
ax.set_ylabel("吞吐 (Mbit/s)", fontsize=12); ax.set_ylim(0, 230)
ax.set_title("方法：mac80211 airtime_weight（ATF）——权重 16:1，吞吐提升有限", fontsize=13, pad=10)
ax.legend(fontsize=10, frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.4)
save(fig, "atf_vip.png")

# ---------- 12. AC 策略 VIP 各组 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
# 左：5G 同频（快 STA）+ 慢 STA
labels = ["基线", "VIP=快 STA\n(WLAN3)", "VIP=慢 STA\n(WLAN5)"]
a = [161.3, 147.0, 112.2]   # WLAN3 快
b = [133.3, 70.9, 80.2]     # WLAN5 慢
x = np.arange(3); w = 0.32
axes[0].bar(x - w / 2, a, w, label="WLAN3（快 STA）", color=C1)
axes[0].bar(x + w / 2, b, w, label="WLAN5（慢 STA）", color=C2)
for i in range(3):
    axes[0].text(x[i] - w / 2, a[i] + 4, f"{a[i]:.1f}", ha="center", fontsize=9)
    axes[0].text(x[i] + w / 2, b[i] + 4, f"{b[i]:.1f}", ha="center", fontsize=9)
axes[0].set_xticks(x); axes[0].set_xticklabels(labels, fontsize=9)
axes[0].set_ylabel("吞吐 (Mbit/s)", fontsize=11)
axes[0].set_title("5G 同频：VIP=快 STA → 2.07:1；\nVIP=慢 STA → 0.71（无效）", fontsize=11)
axes[0].set_ylim(0, 200)
# 右：2.4G 同型号 + 跨频
labels2 = ["2.4G 基线", "2.4G VIP=WLAN6", "跨频基线\n(5G/2.4G)", "跨频 VIP=5G\n(EF)"]
vip_v = [11.4, 41.0, 403.3, 210.0]
norm_v = [9.3, 0.8, 5.0, 5.0]
x2 = np.arange(4); w2 = 0.32
axes[1].bar(x2 - w2 / 2, vip_v, w2, label="VIP 侧", color=C1)
axes[1].bar(x2 + w2 / 2, norm_v, w2, label="普通侧", color=C2)
for i in range(4):
    axes[1].text(x2[i] - w2 / 2, vip_v[i] + 4, f"{vip_v[i]:.1f}", ha="center", fontsize=9)
    axes[1].text(x2[i] + w2 / 2, norm_v[i] + 4, f"{norm_v[i]:.1f}", ha="center", fontsize=9)
axes[1].set_xticks(x2); axes[1].set_xticklabels(labels2, fontsize=9)
axes[1].set_ylabel("吞吐 (Mbit/s)", fontsize=11)
axes[1].set_title("2.4G 同型号强优先（普通饿死）；\n跨频隔离 80.7:1 → EF 后 42.0:1", fontsize=11)
axes[1].set_ylim(0, 460)
for ax_ in axes:
    ax_.spines["top"].set_visible(False); ax_.spines["right"].set_visible(False)
    ax_.grid(axis="y", linestyle="--", alpha=0.4)
fig.suptitle("方法：AC 策略 VIP（nft DSCP→VO）与频段隔离——效果依赖 VIP 链路速率", fontsize=12, y=1.04)
fig.legend(loc="lower center", ncol=2, fontsize=10, frameon=False, bbox_to_anchor=(0.5, -0.02))
save(fig, "ac_policy_vip.png")

print("ALL DONE ->", OUT)
