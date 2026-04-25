# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Automated analysis pipeline for measuring **Privacy Policy Disclosure-Practice Gaps** in Korean domestic startup websites — detecting whether a site's actual tracking behavior matches what its privacy policy discloses.

## Key Results (N=526, April 2026 snapshot)

- 87.5% of sites have third-party trackers (avg 11.6 per site)
- 75.1% under-disclosure (trackers present, policy silent)
- 13.7% of policies explicitly mention third-party trackers
- Highest mismatch: fintech 84.6%, gaming 80.0%, ecommerce 76.5%

## Data Collection

Seed data: `data/external/seed_companies.csv` — 117 curated Korean startups across 12 industries.

Multi-source collection is configured in `configs/base.yaml` under `collection.sources`:
- `manual` (enabled by default) — loads the seed CSV
- `msme` (enabled by default) — MSME 벤처기업 명단 CSV (`data/external/msme_ventures_20250228.csv`)
- `kstartup` (disabled) — data.go.kr 벤처기업 API; set `KSTARTUP_API_KEY` env var to enable
- `demoday` (disabled) — scrapes demoday.co.kr listings

To add sources, set `enabled: true` and rerun `collect-companies`. Deduplication runs automatically (URL-first, then name similarity ≥ 0.88).

## Commands

```bash
# Install dependencies (uses uv, not pip)
uv sync

# Install Playwright browser (required once)
uv run playwright install chromium

# Run the full 8-stage pipeline
uv run python -m src.main run-all --config configs/base.yaml

# Run individual stages
uv run python -m src.main collect-companies --config configs/base.yaml
uv run python -m src.main crawl-sites      --config configs/base.yaml
uv run python -m src.main extract-policies --config configs/base.yaml
uv run python -m src.main detect-trackers  --config configs/base.yaml
uv run python -m src.main evaluate-llm     --config configs/base.yaml
uv run python -m src.main compute-mismatch --config configs/base.yaml
uv run python -m src.main run-stats        --config configs/base.yaml
uv run python -m src.main build-report     --config configs/base.yaml
```

## Architecture

### 8-Stage Pipeline (all orchestrated by `src/main.py` via Typer CLI)

```
collect-companies  →  companies.csv
crawl-sites        →  raw HTML pages (Playwright, async, BFS)
extract-policies   →  text paragraphs (BeautifulSoup)
detect-trackers    →  third-party network requests (Playwright interception)
evaluate-llm       →  compliance JSON (OpenAI GPT-4 or MockEvaluator)
compute-mismatch   →  category-level gap scores
run-stats          →  hypothesis tests (chi-square, Fisher, Mann-Whitney, logistic regression)
build-report       →  CSV tables + matplotlib PNGs
```

### Module Map

| Path | Responsibility |
|---|---|
| `src/main.py` | Typer CLI — 8 commands + `run_all` |
| `src/crawling/crawler.py` | `PolicyCrawler` — async Playwright BFS over site pages |
| `src/crawling/robots.py` | `is_allowed()` — robots.txt compliance |
| `src/extraction/extractor.py` | `PolicyExtractor` — HTML → clean text |
| `src/tracking/tracker.py` | `TrackerDetector` — network request classification into 6 tracker categories |
| `src/llm/evaluator.py` | `BasePolicyEvaluator`, `OpenAIPolicyEvaluator`, `MockPolicyEvaluator`; `get_evaluator()` factory |
| `src/mismatch/calculator.py` | `MismatchCalculator` — under/over/composite gap computation |
| `src/stats/analyzer.py` | `StatsAnalyzer` — statistical tests |

### Data Layout

```
data/raw/        — downloaded HTML
data/interim/    — extracted text, tracker logs
data/processed/  — mismatch scores, stats results
outputs/tables/  — CSV summaries
outputs/figures/ — PNG charts
outputs/logs/
```

### Key Patterns

- **Configuration injection**: all modules accept dicts loaded from `configs/base.yaml`; no hardcoded paths or parameters.
- **Factory for LLM**: `get_evaluator(config)` returns `MockPolicyEvaluator` or `OpenAIPolicyEvaluator`; use the mock for offline/test runs.
- **Pydantic schema**: `ComplianceEvaluation` in `src/llm/evaluator.py` validates LLM JSON output strictly.
- **Async I/O**: `PolicyCrawler` and `TrackerDetector` use `asyncio`; call them with `asyncio.run()` from synchronous pipeline steps.
- **Staged data**: each pipeline stage reads from the previous stage's output directory, enabling partial reruns.

### Tracker Categories (defined in `configs/base.yaml`)

Analytics, Advertising, Session Replay, Social/Embedded, Fingerprinting, Unknown Third-party.

## Configuration

Central config is `configs/base.yaml`. Key tunables:
- `crawling.rate_limit_ms`, `crawling.headless`, `crawling.max_bfs_depth`
- `crawling.anchor_keywords` — Korean + English terms used to locate privacy policy links
- `llm.model`, `llm.temperature` (set to 0.0 for determinism), `llm.use_mock`
- `project.random_seed` — fixed at 42 for reproducibility

Set `llm.use_mock: true` to run the full pipeline without an API key (keyword-based MockPolicyEvaluator).

## Utility Scripts

```bash
uv run python scripts/check_coverage.py   # URL 확보율 및 업종별 분포 확인
uv run python scripts/show_results.py     # 파이프라인 실행 결과 요약
```

Reproducibility notes: `docs/reproducibility_ko.md`. LLM outputs are non-deterministic even at temperature 0.0; web content changes over time.
