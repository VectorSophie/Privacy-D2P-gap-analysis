"""Publication-quality figures for paper.md (Korean labels, JKIISC style)."""

import json
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

OUT = Path("outputs/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Font: try Malgun Gothic (Windows Korean), fall back to default
# ------------------------------------------------------------------
KR_FONT = None
for name in ["Malgun Gothic", "NanumGothic", "AppleGothic", "sans-serif"]:
    try:
        fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        KR_FONT = name
        break
    except Exception:
        continue

if KR_FONT:
    plt.rcParams["font.family"] = KR_FONT
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

# ------------------------------------------------------------------
# Fig 1. Disclosure-Practice Gap 파이 차트
# ------------------------------------------------------------------
labels_kr = ["미공개\n(under-disclosure)", "일치\n(none)", "과공개\n(over-disclosure)"]
sizes = [395, 124, 7]
colors = ["#E05C5C", "#5B9BD5", "#70AD47"]
explode = (0.04, 0, 0)

fig, ax = plt.subplots(figsize=(7, 6))
wedges, texts, autotexts = ax.pie(
    sizes, labels=labels_kr, autopct="%1.1f%%",
    colors=colors, explode=explode,
    startangle=140, pctdistance=0.72,
    textprops={"fontsize": 12},
)
for at in autotexts:
    at.set_fontsize(12)
    at.set_fontweight("bold")
ax.set_title("그림 1. Disclosure-Practice Gap 분류 결과 (N=526)", fontsize=13, pad=14)
fig.tight_layout()
fig.savefig(OUT / "fig1_gap_pie.png", bbox_inches="tight")
plt.close()
print("fig1_gap_pie.png saved")

# ------------------------------------------------------------------
# Fig 2. 업종별 under-disclosure 비율 (수평 막대그래프)
# ------------------------------------------------------------------
industries = [
    "핀테크", "게임", "이커머스", "SaaS", "미디어",
    "에듀테크", "푸드테크", "물류", "모빌리티", "프롭테크", "헬스테크"
]
rates = [84.6, 80.0, 76.5, 75.9, 75.0, 72.4, 71.4, 66.7, 66.7, 62.5, 61.9]
ns =    [13,   30,   17,  352,  40,   29,   7,    6,    3,    8,    21]

# sort ascending for horizontal bar
order = np.argsort(rates)
industries_s = [industries[i] for i in order]
rates_s      = [rates[i]      for i in order]
ns_s         = [ns[i]         for i in order]

colors_bar = ["#E05C5C" if r >= 75 else "#5B9BD5" for r in rates_s]

fig, ax = plt.subplots(figsize=(8, 5.5))
bars = ax.barh(industries_s, rates_s, color=colors_bar, edgecolor="white", height=0.65)
for bar, r, n in zip(bars, rates_s, ns_s):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{r}%  (n={n})", va="center", ha="left", fontsize=10)
ax.set_xlim(0, 100)
ax.set_xlabel("under-disclosure 비율 (%)", fontsize=11)
ax.axvline(75.1, color="gray", linestyle="--", linewidth=1, alpha=0.7)
ax.text(75.4, -0.6, "전체 평균\n75.1%", color="gray", fontsize=8.5, va="top")
ax.set_title("그림 2. 업종별 under-disclosure 비율 (N=526)", fontsize=13, pad=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig2_industry_bar.png", bbox_inches="tight")
plt.close()
print("fig2_industry_bar.png saved")

# ------------------------------------------------------------------
# Fig 3. 서드파티 트래커 카테고리별 분포
# ------------------------------------------------------------------
categories = ["Unknown\nThird-party", "Analytics", "Advertising", "Social/\nEmbedded", "Session\nReplay"]
counts     = [2363, 1771, 1156, 28, 16]
pcts       = [44.3, 33.2, 21.7, 0.5, 0.3]
cat_colors = ["#8B8B8B", "#5B9BD5", "#E05C5C", "#70AD47", "#FFC000"]

fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(categories))
b = ax.bar(x, counts, color=cat_colors, edgecolor="white", width=0.6)
for bar, cnt, pct in zip(b, counts, pcts):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
            f"{cnt:,}\n({pct}%)", ha="center", va="bottom", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylabel("탐지 건수", fontsize=11)
ax.set_ylim(0, 2800)
ax.set_title("그림 3. 서드파티 트래커 카테고리별 분포 (총 5,334건)", fontsize=13, pad=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig3_tracker_categories.png", bbox_inches="tight")
plt.close()
print("fig3_tracker_categories.png saved")

# ------------------------------------------------------------------
# Fig 4. LLM 분류기 성능 비교 (Grouped bar)
# ------------------------------------------------------------------
metrics = ["Precision", "Recall", "F1-score", "Cohen's κ"]
rule    = [0.226, 1.000, 0.369, 0.216]
llm     = [0.478, 0.917, 0.629, 0.559]

x = np.arange(len(metrics))
w = 0.32
fig, ax = plt.subplots(figsize=(7, 4.5))
b1 = ax.bar(x - w/2, rule, w, label="Rule-based Baseline", color="#8B8B8B", edgecolor="white")
b2 = ax.bar(x + w/2, llm,  w, label="LLM (GPT-4 Turbo)",  color="#5B9BD5", edgecolor="white")
for bar, v in zip(list(b1) + list(b2), rule + llm):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
            f"{v:.3f}", ha="center", va="bottom", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylim(0, 1.2)
ax.set_ylabel("점수", fontsize=11)
ax.legend(fontsize=10)
ax.set_title("그림 4. LLM 분류기 성능 비교 (N=100 수동 검증 샘플)", fontsize=13, pad=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig4_classifier_performance.png", bbox_inches="tight")
plt.close()
print("fig4_classifier_performance.png saved")

print("\n모든 그림 저장 완료:", OUT)
