"""
Multi-LLM comparative evaluation for privacy policy tracker disclosure classification.
Uses OpenRouter API. Saves results to data/processed/multi_llm_eval.json.

Usage:
    uv run python scripts/multi_llm_eval.py          # full run
    uv run python scripts/multi_llm_eval.py --test 5  # quick smoke-test
    uv run python scripts/multi_llm_eval.py --dry-run # metrics only from cached data
"""

import argparse
import json
import csv
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MAX_CHARS = 6000

MODELS = {
    "GPT-4 Turbo":           None,                               # already in groundtruth CSV
    "Claude Sonnet 4.6":     "anthropic/claude-sonnet-4.6",
    "Gemini 2.5 Flash":      "google/gemini-2.5-flash",
    "Llama 4 Maverick":      "meta-llama/llama-4-maverick",
    "Mistral Large 2512":    "mistralai/mistral-large-2512",
}

SYSTEM_PROMPT = (
    "당신은 한국 개인정보보호법(PIPA) 전문 컴플라이언스 분석기입니다. "
    "주어진 개인정보 처리방침 텍스트에서 서드파티 트래커, 쿠키, "
    "행태정보 수집, 외부 분석(애널리틱스) 서비스에 대한 명시적 언급 여부를 판단하세요. "
    "일반적인 '제3자에게 제공하지 않음' 선언은 공시로 인정하지 않습니다. "
    "Google Analytics, Meta Pixel, TikTok Pixel 등 특정 서비스명 또는 "
    "행태정보 수집에 관한 명시적 기재가 있어야 공시로 분류합니다. "
    "반드시 다음 JSON 형식으로만 응답하세요:\n"
    '{"mentions_third_party_trackers": true}\n'
    "또는\n"
    '{"mentions_third_party_trackers": false}'
)


def _parse_result(raw: str) -> bool:
    try:
        return bool(json.loads(raw).get("mentions_third_party_trackers", False))
    except Exception:
        low = raw.lower()
        if '"mentions_third_party_trackers": true' in low:
            return True
        if '"mentions_third_party_trackers": false' in low:
            return False
        # last-resort: look for bare true/false JSON value
        if ": true" in low:
            return True
        return False


def evaluate_one(text: str, model_id: str, client: OpenAI) -> bool | None:
    text = text[:MAX_CHARS]
    if not text.strip():
        return False

    for attempt in range(3):
        try:
            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"처리방침 텍스트:\n\n{text}"},
            ]
            try:
                resp = client.chat.completions.create(
                    model=model_id, temperature=0.0, max_tokens=64,
                    response_format={"type": "json_object"}, messages=msgs,
                )
            except Exception:
                resp = client.chat.completions.create(
                    model=model_id, temperature=0.0, max_tokens=64, messages=msgs,
                )
            return _parse_result(resp.choices[0].message.content)
        except Exception as exc:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                print(f"\n    FAILED: {exc}")
                return None


def compute_metrics(preds: list, truth: list) -> dict:
    pairs = [(p, g) for p, g in zip(preds, truth) if p is not None]
    n = len(pairs)
    tp = sum(p and g for p, g in pairs)
    fp = sum(p and not g for p, g in pairs)
    fn = sum(not p and g for p, g in pairs)
    tn = sum(not p and not g for p, g in pairs)

    prec = tp / (tp + fp) if tp + fp else 0.0
    rec  = tp / (tp + fn) if tp + fn else 0.0
    f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    p_o = (tp + tn) / n if n else 0.0
    p_e = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n * n) if n else 0.0
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0

    return {
        "precision": round(prec, 3), "recall": round(rec, 3),
        "f1": round(f1, 3), "kappa": round(kappa, 3),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n_evaluated": n,
    }


def main(dry_run: bool = False, test_n: int = 0):
    if not OPENROUTER_API_KEY:
        raise SystemExit("ERROR: OPENROUTER_API_KEY not found in environment or .env")

    with open("data/interim/annotation_sample.json", encoding="utf-8") as f:
        sample_data = json.load(f)
    with open("data/interim/annotation_groundtruth.csv", encoding="utf-8") as f:
        gt_rows = list(csv.DictReader(f))

    gt_map   = {r["company_id"]: r["my_label"] == "True" for r in gt_rows}
    gpt4_map = {r["company_id"]: r["gpt4"] == "True"     for r in gt_rows}

    company_ids = list(sample_data.keys())
    if test_n:
        company_ids = company_ids[:test_n]

    texts = [sample_data[cid]["text"] for cid in company_ids]
    truth = [gt_map[cid] for cid in company_ids]
    gpt4_preds = [gpt4_map[cid] for cid in company_ids]

    n_pos = sum(truth)
    print(f"Dataset: N={len(company_ids)}, positive={n_pos}, negative={len(company_ids)-n_pos}")

    results: dict = {}
    results["GPT-4 Turbo"] = compute_metrics(gpt4_preds, truth)
    print(f"GPT-4 Turbo (pre-existing): {results['GPT-4 Turbo']}")

    if dry_run:
        print("\nDry-run — skipping API calls.")
        _print_summary(results)
        return

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=BASE_URL)
    partial_path = Path("data/processed/multi_llm_partial.json")
    raw_preds: dict = {}
    if partial_path.exists():
        with open(partial_path, encoding="utf-8") as f:
            raw_preds = json.load(f)
        print(f"Resuming partial results: {list(raw_preds.keys())}")

    for model_name, model_id in MODELS.items():
        if model_id is None:
            continue

        cached = raw_preds.get(model_name, [])
        if len(cached) >= len(company_ids):
            print(f"{model_name}: loaded from cache ({len(cached)} results)")
            preds = cached[: len(company_ids)]
        else:
            print(f"\n→ Evaluating {model_name} ({model_id})...")
            preds = list(cached)
            start = len(preds)
            for i in range(start, len(company_ids)):
                pred = evaluate_one(texts[i], model_id, client)
                preds.append(pred)
                if (i + 1) % 10 == 0 or (i + 1) == len(company_ids):
                    print(f"  [{i+1}/{len(company_ids)}]", end="\r")
                time.sleep(0.25)
                if (i + 1) % 25 == 0:
                    raw_preds[model_name] = preds
                    with open(partial_path, "w", encoding="utf-8") as f:
                        json.dump(raw_preds, f, ensure_ascii=False)
            raw_preds[model_name] = preds
            print()

        results[model_name] = compute_metrics(preds, truth)
        print(f"  {model_name}: {results[model_name]}")

    output = {
        "metadata": {
            "n_samples": len(company_ids), "n_positive": n_pos,
            "n_negative": len(company_ids) - n_pos,
        },
        "models": results,
        "raw_predictions": raw_preds,
    }
    out_path = Path("data/processed/multi_llm_eval.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    if partial_path.exists():
        partial_path.unlink()

    _print_summary(results)
    print(f"\nSaved → {out_path}")


def _print_summary(results: dict):
    print("\n=== MULTI-LLM EVALUATION SUMMARY ===")
    print(f"{'Model':<22} {'Prec':>7} {'Rec':>7} {'F1':>7} {'κ':>7}")
    print("-" * 55)
    for m, r in results.items():
        print(f"{m:<22} {r['precision']:>7.3f} {r['recall']:>7.3f} {r['f1']:>7.3f} {r['kappa']:>7.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Skip API calls, show GPT-4 only")
    ap.add_argument("--test", type=int, default=0, metavar="N", help="Evaluate first N samples only")
    args = ap.parse_args()
    main(dry_run=args.dry_run, test_n=args.test)
