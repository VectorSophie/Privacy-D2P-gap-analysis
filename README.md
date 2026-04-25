# Privacy Disclosure Gap Analysis

국내 스타트업 웹사이트를 대상으로 개인정보 처리방침의 컴플라이언스 실태와 실제 서드파티 트래커 운영 간의 불일치(Disclosure–Practice Gap)를 자동 분석하는 연구용 파이프라인입니다.

> **논문**: 백동재·오준형, "동적 LLM 웹 스크래핑을 활용한 국내 스타트업 개인정보 처리방침 컴플라이언스 실태 분석"

## 주요 분석 결과 (N=526)

| 지표 | 수치 |
|---|---|
| 서드파티 트래커 탐지율 | **87.5%** (460/526개사) |
| 사이트당 평균 트래커 수 | **11.6개** (트래커 보유 기업 기준) |
| Under-disclosure 비율 | **75.1%** (395/526) — 트래커 운영 중이나 처리방침 미기재 |
| 트래커 보유 기업의 미공개율 | **85.9%** (395/460) |
| 처리방침 내 트래커 명시율 | **13.7%** (72/526) |
| 법적 필수 항목 충족률 | **54.9%** (289/526) |

## 파이프라인 구조 (8단계)

```
collect-companies  →  companies.csv
crawl-sites        →  raw HTML (Playwright, async BFS)
extract-policies   →  처리방침 텍스트 (BeautifulSoup)
detect-trackers    →  서드파티 네트워크 요청 (Playwright 인터셉트)
evaluate-llm       →  컴플라이언스 JSON (GPT-4 Turbo)
compute-mismatch   →  Under/Over-disclosure 레이블
run-stats          →  통계 검정 결과 (카이제곱, Mann-Whitney 등)
build-report       →  CSV 테이블 + matplotlib 시각화
```

## 설치

```bash
# 의존성 설치 (uv 사용)
uv sync

# Playwright 브라우저 설치 (최초 1회)
uv run playwright install chromium
```

## 환경 변수

```bash
# .env 파일 생성 후 API 키 설정
OPENAI_API_KEY=sk-...
```

## 실행

```bash
# 전체 파이프라인 일괄 실행
uv run python -m src.main run-all --config configs/base.yaml

# 단계별 실행
uv run python -m src.main collect-companies --config configs/base.yaml
uv run python -m src.main crawl-sites      --config configs/base.yaml
uv run python -m src.main extract-policies --config configs/base.yaml
uv run python -m src.main detect-trackers  --config configs/base.yaml
uv run python -m src.main evaluate-llm     --config configs/base.yaml
uv run python -m src.main compute-mismatch --config configs/base.yaml
uv run python -m src.main run-stats        --config configs/base.yaml
uv run python -m src.main build-report     --config configs/base.yaml
```

## LLM 설정

`configs/base.yaml`의 `llm` 섹션에서 제어합니다.

```yaml
llm:
  model: "gpt-4-turbo"   # 사용할 모델
  temperature: 0.0        # 결정론적 출력을 위해 0.0 고정
  use_mock: false         # true로 변경 시 API 없이 키워드 기반 Mock 평가
```

`use_mock: true`로 설정하면 API 키 없이도 파이프라인 전체를 테스트할 수 있습니다.

## 보조 스크립트

```bash
# 크롤링 커버리지 확인 (URL 확보율, 업종별 분포)
uv run python scripts/check_coverage.py

# 파이프라인 실행 결과 요약 출력
uv run python scripts/show_results.py
```

## 문서

| 파일 | 내용 |
|---|---|
| [docs/methodology_ko.md](docs/methodology_ko.md) | 전체 방법론 상세 기술 |
| [docs/experiment_design_ko.md](docs/experiment_design_ko.md) | 표본 설계·검증·통계 분석 계획 |
| [docs/reproducibility_ko.md](docs/reproducibility_ko.md) | 재현성 가이드 및 유의사항 |
| [docs/tech_stack_rationale_ko.md](docs/tech_stack_rationale_ko.md) | 기술 스택 선정 근거 |
| [docs/decisions.md](docs/decisions.md) | 구조적·기술적 설계 결정 기록 (ADR) |
