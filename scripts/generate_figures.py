"""Publication-quality figures for paper.md (Korean labels, JKIISC style)."""

import json
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
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

# Colour palette (colour-blind friendly, academic)
C_BLUE   = "#2B6CB0"
C_TEAL   = "#2C7A7B"
C_GREEN  = "#276749"
C_ORANGE = "#C05621"
C_RED    = "#C53030"
C_GRAY   = "#4A5568"
C_LGRAY  = "#E2E8F0"


# ------------------------------------------------------------------
# Fig 0. Research Methodology Pipeline (academic flowchart)
# ------------------------------------------------------------------
steps = [
    ("S1", "연구 모집단 구성",    "Research Population",   "1,000 Korean Startups",        C_BLUE),
    ("S2", "동적 웹 크롤링·수집", "Dynamic Web Collection","BFS Crawling · N=957 URLs",     C_TEAL),
    ("S3", "서드파티 트래커 탐지","Tracker Detection",     "Network Interception · 6 Categories", C_GREEN),
    ("S4", "처리방침 텍스트 추출","Policy Text Extraction","NLP Parsing · N=526 Valid Docs", C_TEAL),
    ("S5", "LLM 기반 공시 분류",  "LLM Disclosure Classification","GPT-4 Turbo · Structured Prompting", C_BLUE),
    ("S6", "Disclosure-Practice Gap 측정","Gap Measurement","2×2 Classification Matrix",   C_ORANGE),
    ("S7", "통계 분석",           "Statistical Analysis",  "z-test · Spearman ρ",          C_GRAY),
]

fig, ax = plt.subplots(figsize=(8.5, 11))
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis("off")

# Title
ax.text(5, 13.3, "그림 1. 연구 방법론 프레임워크", fontsize=14,
        fontweight="bold", ha="center", va="center")
ax.text(5, 12.85, "Figure 1. Research Methodology Framework",
        fontsize=10, ha="center", va="center", color=C_GRAY)

BOX_W, BOX_H = 7.0, 1.02
X0 = 1.5
Y_START = 12.0
Y_STEP  = 1.55

for i, (sid, kr, en, detail, col) in enumerate(steps):
    y = Y_START - i * Y_STEP
    # Outer box (light fill)
    rect = FancyBboxPatch((X0, y - BOX_H / 2), BOX_W, BOX_H,
                           boxstyle="round,pad=0.08", linewidth=1.4,
                           edgecolor=col, facecolor=col + "18")
    ax.add_patch(rect)
    # Left accent strip
    accent = FancyBboxPatch((X0, y - BOX_H / 2), 0.42, BOX_H,
                             boxstyle="round,pad=0.0", linewidth=0,
                             facecolor=col, zorder=2)
    ax.add_patch(accent)
    # Step number
    ax.text(X0 + 0.21, y, sid, fontsize=9, fontweight="bold",
            color="white", ha="center", va="center", zorder=3)
    # Korean label
    ax.text(X0 + 0.65, y + 0.15, kr, fontsize=11, fontweight="bold",
            ha="left", va="center", color="#1A202C")
    # English sub-label
    ax.text(X0 + 0.65, y - 0.15, en, fontsize=8.5,
            ha="left", va="center", color=C_GRAY, style="italic")
    # Detail annotation (right side)
    ax.text(X0 + BOX_W - 0.12, y, detail, fontsize=8,
            ha="right", va="center", color=col)

    # Downward arrow between boxes
    if i < len(steps) - 1:
        y_arrow_top = y - BOX_H / 2
        y_arrow_bot = y_arrow_top - (Y_STEP - BOX_H)
        ax.annotate("", xy=(5, y_arrow_bot + 0.02),
                    xytext=(5, y_arrow_top - 0.02),
                    arrowprops=dict(arrowstyle="-|>", color=C_GRAY,
                                   lw=1.5, mutation_scale=14))

fig.tight_layout(pad=0)
fig.savefig(OUT / "fig0_methodology_flow.png", bbox_inches="tight", dpi=150)
plt.close()
print("fig0_methodology_flow.png saved")


# ------------------------------------------------------------------
# Fig 1. Disclosure-Practice Gap 파이 차트
# ------------------------------------------------------------------
labels_kr = ["미공개\n(under-disclosure)", "일치\n(none)", "과공개\n(over-disclosure)"]
sizes = [395, 124, 7]
colors = [C_RED, C_BLUE, "#70AD47"]
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
ax.set_title("그림 2. Disclosure-Practice Gap 분류 결과 (N=526)", fontsize=13, pad=14)
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
ns    = [13,   30,   17,  352,  40,   29,   7,    6,    3,    8,    21]

order = np.argsort(rates)
industries_s = [industries[i] for i in order]
rates_s      = [rates[i]      for i in order]
ns_s         = [ns[i]         for i in order]
# Small-N industries (< 10) shown with lighter colour
colors_bar = []
for r, n in zip(rates_s, ns_s):
    if n < 10:
        colors_bar.append(C_BLUE + "70")   # translucent
    elif r >= 75:
        colors_bar.append(C_RED)
    else:
        colors_bar.append(C_BLUE)

fig, ax = plt.subplots(figsize=(8.5, 5.5))
bars = ax.barh(industries_s, rates_s, color=colors_bar, edgecolor="white", height=0.65)
for bar, r, n in zip(bars, rates_s, ns_s):
    note = f"* N={n}" if n < 10 else f"N={n}"
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{r}%  ({note})", va="center", ha="left", fontsize=9.5)
ax.set_xlim(0, 105)
ax.set_xlabel("under-disclosure 비율 (%)", fontsize=11)
ax.axvline(75.1, color=C_GRAY, linestyle="--", linewidth=1, alpha=0.7)
ax.text(75.4, -0.7, "전체 평균\n75.1%", color=C_GRAY, fontsize=8.5, va="top")
ax.text(1, -0.7, "* 표본 수 10 미만 — 해석 주의",
        fontsize=8, color=C_GRAY, va="top", style="italic")
ax.set_title("그림 3. 업종별 under-disclosure 비율 (N=526)", fontsize=13, pad=10)
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
cat_colors = [C_GRAY, C_BLUE, C_RED, C_GREEN, C_ORANGE]

fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(categories))
b = ax.bar(x, counts, color=cat_colors, edgecolor="white", width=0.6)
for bar, cnt, pct in zip(b, counts, pcts):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
            f"{cnt:,}\n({pct}%)", ha="center", va="bottom", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylabel("탐지 건수", fontsize=11)
ax.set_ylim(0, 2900)
ax.set_title("그림 4. 서드파티 트래커 카테고리별 분포 (총 5,334건)", fontsize=13, pad=10)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig3_tracker_categories.png", bbox_inches="tight")
plt.close()
print("fig3_tracker_categories.png saved")


# ------------------------------------------------------------------
# Fig 4. Multi-LLM Comparative Evaluation
# ------------------------------------------------------------------
multi_llm_path = Path("data/processed/multi_llm_eval.json")
if multi_llm_path.exists():
    with open(multi_llm_path, encoding="utf-8") as f:
        llm_data = json.load(f)
    model_results = llm_data["models"]
else:
    # Fallback values
    model_results = {
        "GPT-4 Turbo":        {"precision": 0.478, "recall": 0.917, "f1": 0.629, "kappa": 0.559},
        "Claude Sonnet 4.6":  {"precision": 1.000, "recall": 0.333, "f1": 0.500, "kappa": 0.468},
        "Gemini 2.5 Flash":   {"precision": 0.800, "recall": 0.667, "f1": 0.727, "kappa": 0.694},
        "Llama 4 Maverick":   {"precision": 0.417, "recall": 0.833, "f1": 0.556, "kappa": 0.471},
        "Mistral Large 2512": {"precision": 0.692, "recall": 0.750, "f1": 0.720, "kappa": 0.680},
    }

model_names = list(model_results.keys())
short_names = ["GPT-4\nTurbo", "Claude\nSonnet 4.6", "Gemini\n2.5 Flash",
               "Llama 4\nMaverick", "Mistral\nLarge"]
bar_colors  = [C_BLUE, C_ORANGE, C_TEAL, C_GREEN, C_GRAY]

metrics_keys  = ["precision", "recall", "f1", "kappa"]
metrics_labels = ["Precision", "Recall", "F1-score", "Cohen's κ"]

n_models  = len(model_names)
n_metrics = len(metrics_keys)
x = np.arange(n_metrics)
w = 0.14
offsets = np.linspace(-(n_models - 1) / 2 * w, (n_models - 1) / 2 * w, n_models)

fig, ax = plt.subplots(figsize=(10, 5.5))
for j, (mname, short, col, offset) in enumerate(zip(model_names, short_names, bar_colors, offsets)):
    vals = [model_results[mname][k] for k in metrics_keys]
    bars = ax.bar(x + offset, vals, w, label=short.replace("\n", " "),
                  color=col, edgecolor="white", alpha=0.9)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{v:.2f}", ha="center", va="bottom", fontsize=7.5, color=col,
                fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(metrics_labels, fontsize=12)
ax.set_ylim(0, 1.22)
ax.set_ylabel("점수", fontsize=11)
ax.legend(ncol=5, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, 1.14),
          frameon=False)
ax.set_title("그림 5. LLM 모델별 분류 성능 비교 (N=100 수동 검증 샘플)", fontsize=13, pad=28)
ax.spines[["top", "right"]].set_visible(False)
ax.axhline(0.5, color=C_LGRAY, linewidth=0.8, linestyle="--")
fig.tight_layout()
fig.savefig(OUT / "fig4_classifier_performance.png", bbox_inches="tight")
plt.close()
print("fig4_classifier_performance.png saved")


print("\n모든 그림 저장 완료:", OUT)
