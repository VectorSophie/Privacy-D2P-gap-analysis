import json
import pandas as pd
from pathlib import Path
from collections import Counter

base = Path(".")

# ── 크롤링 결과 ──────────────────────────────────────────────
cr_path = base / "data/interim/crawl_results.json"
if cr_path.exists():
    cr = json.loads(cr_path.read_text(encoding="utf-8"))
    total = len(cr)
    success = sum(1 for d in cr.values() if d["status"] == "success")
    status_cnt = Counter(d["status"] for d in cr.values())
    print("=== 크롤링 결과 ===")
    print(f"처리: {total}개")
    print(f"성공: {success}개 ({success/total*100:.1f}%)")
    for k, v in status_cnt.most_common():
        print(f"  {k}: {v}")
else:
    print("crawl_results.json 없음")

# ── 트래커 탐지 결과 ─────────────────────────────────────────
tr_path = base / "data/interim/trackers.json"
if tr_path.exists():
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    has_tracker = sum(1 for v in tr.values() if len(v) > 0)
    all_cats = [t["category"] for v in tr.values() for t in v]
    cat_cnt = Counter(all_cats)
    print("\n=== 트래커 탐지 결과 ===")
    print(f"분석 기업: {len(tr)}개")
    print(f"트래커 발견: {has_tracker}개 ({has_tracker/len(tr)*100:.1f}%)")
    print("카테고리별:")
    for k, v in cat_cnt.most_common():
        print(f"  {k}: {v}")
else:
    print("\ntrackers.json 없음 (아직 진행 중)")

# ── Mismatch 결과 ─────────────────────────────────────────────
mm_path = base / "data/processed/mismatch.csv"
if mm_path.exists():
    df = pd.read_csv(mm_path)
    print("\n=== Mismatch 결과 ===")
    print(f"분석 기업: {len(df)}개")
    print(f"under_disclosure (트래커 있는데 미공개): {df['under_disclosure'].sum()}")
    print(f"over_disclosure  (공개했는데 트래커 없음): {df['over_disclosure'].sum()}")
    print("\n레이블 분포:")
    print(df["mismatch_label"].value_counts().to_string())
else:
    print("\nmismatch.csv 없음 (아직 진행 중)")
