# 기술 스택 선정 근거 (Tech Stack Rationale)

본 연구의 자동화 분석 파이프라인 구현에 사용된 주요 기술 스택과 그 선정 배경을 학술적·공학적 관점에서 서술한다. 연구 환경의 재현성(Reproducibility)과 분석의 정확성을 최우선 고려하여 설계되었다.

## 1. 환경 관리 및 의존성: uv (vs. pip/poetry)

- **결정론적 빌드(Deterministic Build)**: 본 파이프라인은 Playwright, Pandas, ML/LLM 관련 라이브러리 등 의존성 트리가 깊고 버전 민감도가 높다. `uv`는 Cargo 기반으로 구현되어 기존 `pip`나 `poetry` 대비 의존성 해석 속도가 극도로 빠르며, `uv.lock`을 통해 연구 결과를 검증하려는 제3자가 정확히 동일한 가상환경을 재현할 수 있도록 보장한다.
- **실행 컨텍스트의 격리**: 전역 Python 환경 오염을 방지하고, 실험 스크립트 실행 시 런타임 충돌을 원천 차단한다.

## 2. 웹 크롤링 및 동적 분석: Playwright (vs. Selenium)

- **단일 페이지 애플리케이션(SPA) 대응**: 현대 스타트업 웹사이트는 대부분 CSR(Client-Side Rendering) 방식을 채택하고 있어 단순 HTTP GET(예: `requests` 패키지)으로는 DOM을 온전히 확보할 수 없다. 
- **비동기 API와 Networkidle**: Playwright는 `asyncio`를 네이티브로 지원하며, `wait_until="networkidle"` 옵션을 통해 비동기 렌더링이 완료된 정확한 시점의 HTML DOM 트리를 안정적으로 캡처할 수 있다.
- **네트워크 인터셉트 구조**: Selenium은 네트워크 패킷 캡처를 위해 별도의 외부 프록시(mitmproxy 등)를 구성해야 하나, Playwright는 브라우저 내부 이벤트 훅(`page.on("request")`)을 기본 지원하여 빠르고 누수 없는 트래커 로깅이 가능하다.

## 3. 비동기 처리: asyncio

- **속도와 안정성의 트레이드오프**: 100개 이상의 사이트를 크롤링하고 각각 최대 30초 대기(`timeout_ms=30000`)를 수행할 경우 동기식 처리 시 상당한 병목이 발생한다. `asyncio`를 도입함으로써 I/O 바운드 작업(네트워크 로깅, 크롤링)을 효율적으로 다중 처리하되, `rate_limit_ms` 옵션과 조합하여 대상 서버에 과도한 부하(DDoS로 오인될 소지)를 주지 않도록 밸런스를 조절하였다.

## 4. 데이터 조작 및 통계: Pandas & Scipy & Statsmodels

- **데이터 파이프라인의 표준화**: 원시 JSON 로그 데이터를 Pandas DataFrame으로 변환함으로써 결측치 처리 및 롱 포맷(Long format) 변환이 용이해진다.
- **강건한 통계 검정**: Python 생태계 내에서 학술적으로 널리 검증된 `scipy.stats`와 `statsmodels`를 조합하여 비모수 검정부터 다변량 회귀 분석까지 단일 파이프라인 내에서 자동화가 가능하도록 구성했다.

## 5. 정책 평가 방법론: LLM vs Rule-based Baseline

- **Rule-based 접근의 한계**: 기존의 정규표현식(Regex) 기반 추출 방식은 '관련 법령에 따라', '필요한 범위 내에서'와 같이 정보 주체의 권리를 제약하는 문맥적 모호성(Ambiguity)을 포착하지 못한다.
- **LLM의 시맨틱 분석 도입**: 최신 대형언어모델(GPT-4-Turbo 등)은 문맥 내 함축된 제3자 제공 의무나 트래커 사용 고지를 식별할 수 있다. 
- **정확도와 비용의 트레이드오프 통제**: LLM은 환각(Hallucination) 리스크가 존재하므로, `temperature=0.0`으로 랜덤성을 통제하고 `Pydantic` 스키마를 통해 JSON 구조를 강제했다. 특히, 모든 평가 판단에 대해 원문 텍스트를 발췌(`evidence span`)하도록 설계하여 사후 수동 검증의 용이성을 극대화했다.
