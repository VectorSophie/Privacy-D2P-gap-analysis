# 재현성 가이드 (Reproducibility Guide)

본 문서는 제3자가 동일한 환경에서 분석 파이프라인(데이터 수집, 트래커 탐지, 컴플라이언스 평가, 통계 분석)을 반복 실행하여 동일한 결과를 도출할 수 있도록 지원하기 위한 절차를 기술합니다.

## 1. 실행 환경 요구사항

| 항목 | 요구사항 |
|---|---|
| Python | 3.11 이상 |
| 패키지 관리자 | `uv` (결정론적 빌드 보장) |
| 브라우저 | Chromium (Playwright 내장, `uv run playwright install chromium`) |
| LLM API | OpenAI API 키 (`OPENAI_API_KEY`) — Mock 모드 사용 시 불필요 |

### uv 선택 근거

`uv`는 `uv.lock` 파일을 기반으로 결정론적(deterministic)인 설치를 보장합니다. Playwright, Pandas, OpenAI SDK 등 의존성 트리가 깊은 라이브러리를 포함하므로, `pip`나 `poetry` 대비 버전 충돌 없는 환경 재구축이 가능합니다.

## 2. 환경 구축

```bash
# 1. 가상환경 생성 및 의존성 설치
uv sync

# 2. Playwright 브라우저 설치 (최초 1회)
uv run playwright install chromium

# 3. API 키 설정
#    프로젝트 루트에 .env 파일을 생성하고 아래 내용을 기입합니다.
echo "OPENAI_API_KEY=sk-..." > .env
```

**Mock 모드 (API 키 없이 테스트):** `configs/base.yaml`에서 `llm.use_mock: true`로 변경하면 GPT-4 호출 없이 키워드 기반 평가기로 파이프라인 전체를 실행할 수 있습니다.

## 3. 재현 절차

파이프라인의 모든 모듈은 `configs/base.yaml`을 통해 파라미터가 주입됩니다.

### 단계별 실행

```bash
uv run python -m src.main collect-companies --config configs/base.yaml
uv run python -m src.main crawl-sites      --config configs/base.yaml
uv run python -m src.main extract-policies --config configs/base.yaml
uv run python -m src.main detect-trackers  --config configs/base.yaml
uv run python -m src.main evaluate-llm     --config configs/base.yaml
uv run python -m src.main compute-mismatch --config configs/base.yaml
uv run python -m src.main run-stats        --config configs/base.yaml
uv run python -m src.main build-report     --config configs/base.yaml
```

각 단계의 출력은 `data/` 및 `outputs/` 하위 디렉터리에 저장되며, 다음 단계의 입력으로 사용됩니다.

### 일괄 실행

```bash
uv run python -m src.main run-all --config configs/base.yaml
```

## 4. 본 연구의 실행 결과 (2026년 4월 기준 스냅샷)

| 지표 | 수치 |
|---|---|
| 분석 모집단 | 1,000개사 (URL 확보 957개) |
| 처리방침 크롤링 성공 | 526개사 (54.9%) |
| 트래커 탐지 기업 | 460개사 (87.5%) |
| Under-disclosure | 395개사 (75.1%) |
| LLM 모델 | GPT-4 Turbo (`gpt-4-turbo`) |
| LLM temperature | 0.0 |

## 5. 재현 시 유의사항

1. **웹 환경의 변동성**: 대상 스타트업 웹사이트의 DOM 구조나 트래커 정책은 실시간으로 변경됩니다. 크롤링·트래커 탐지 단계를 완전히 동일하게 재현하려면 본 연구진이 수집한 `data/raw/` 및 `data/interim/` 스냅샷 데이터를 사용해야 합니다.

2. **LLM 평가의 비결정성**: `temperature=0.0`으로 설정하여 최대한 결정론적 출력을 유도하지만, OpenAI 측 모델 업데이트에 따라 미세한 평가 변동이 발생할 수 있습니다. 본 연구는 `gpt-4-turbo` (`2024-04-09` 버전)를 기준으로 작성되었습니다.

3. **난수 시드 통제**: 표본 추출 및 통계 분석의 랜덤성은 `configs/base.yaml`의 `project.random_seed: 42`로 통제됩니다.

4. **robots.txt 차단**: 대상 기업 중 일부는 robots.txt를 통해 크롤러를 차단합니다. 이 기업들은 결과에서 제외되며 survivorship bias의 원인이 될 수 있습니다.
