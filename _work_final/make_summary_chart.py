# -*- coding: utf-8 -*-
"""生成三组方法 VIP:普通 吞吐比对比汇总图"""
import os
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

OUT = r"D:\Desktop\AI 辅助对话\_work_final\charts"
os.makedirs(OUT, exist_ok=True)

cats = [
    "方法一 WDRR\n（配置 4:1）",
    "方法二 ATF\n快 STA",
    "方法二 ATF\n慢 STA",
    "方法三 5G\n快 STA",
    "方法三 5G\n慢 STA",
    "方法三 2.4G\n同型号",
    "方法三 跨频\n（EF 后）",
]
vals = [1.02, 1.14, 0.77, 2.07, 0.71, 51.3, 42.0]
colors = ["#B05555", "#B05555", "#B05555", "#2F6FB6", "#B05555", "#2F6FB6", "#2F6FB6"]

fig, ax = plt.subplots(figsize=(10, 4.8))
bars = ax.barh(cats, vals, color=colors, height=0.6)
ax.axvline(1.0, color="#646A73", ls="--", lw=1.2)
ax.text(1.02, 6.9, "比值=1（无效果）", fontsize=9, color="#646A73")
for b, v in zip(bars, vals):
    ax.text(v * 1.03, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=10, fontweight="bold")
ax.set_xscale("log")
ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50, 100])
ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100"])
ax.set_xlabel("VIP:普通 吞吐比（对数刻度）", fontsize=12)
ax.set_title("三组方法效果对比：只有方法三（AC 策略）在快 STA / 隔离场景 >2，方法一、二接近无效", fontsize=13, pad=10)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "method_summary.png"), dpi=150, bbox_inches="tight", facecolor="white")
print("saved method_summary.png")
