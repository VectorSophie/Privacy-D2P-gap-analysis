import abc
import json
import logging
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()


# -----------------------------------------------------------------------------
# 1. JSON Schema 정의 (Pydantic 모델 활용)
# -----------------------------------------------------------------------------
class ComplianceEvaluation(BaseModel):
    """
    LLM이 개인정보 처리방침 텍스트를 분석하고 반환해야 하는 엄격한 JSON 구조입니다.
    Pydantic을 활용하여 Schema Validation 및 OpenAI 함수 호출(Function Calling)에 활용 가능합니다.
    """
    has_mandatory_items: bool = Field(..., description="수집 목적, 항목, 기간 등 주요 법적 필수 항목이 모두 명시되어 있는지 여부")
    mandatory_items_evidence: Optional[str] = Field(None, description="필수 항목 명시 또는 누락에 대한 본문 내 텍스트 발췌 근거(evidence span)")
    
    ambiguity_detected: bool = Field(..., description="'필요 시', '관련 법령에 따라' 등 정보 주체에게 명확한 정보를 주지 않는 모호한 표현(Ambiguity) 존재 여부")
    ambiguity_evidence: Optional[str] = Field(None, description="발견된 모호한 표현의 텍스트 발췌(span)")
    
    legal_omission_detected: bool = Field(..., description="권리 행사 방법, 보호책임자, 파기 절차 등 명백한 법적 필수 고지 의무의 누락 여부")
    legal_omission_evidence: Optional[str] = Field(None, description="누락되었다고 판단한 사유 또는 해당 섹션 부재에 대한 설명")
    
    mentions_third_party_trackers: bool = Field(..., description="서드파티 트래커, 쿠키, 행태정보 수집, 외부 애널리틱스 등에 대한 명시적 언급 여부")
    tracker_evidence: Optional[str] = Field(None, description="트래커 운영과 관련된 텍스트 발췌(span)")


# -----------------------------------------------------------------------------
# 2. Base Evaluator 구조 (추상 클래스)
# -----------------------------------------------------------------------------
class BasePolicyEvaluator(abc.ABC):
    def __init__(self, temperature: float = 0.0):
        # 재현성(Reproducibility)을 위해 temperature를 0.0으로 고정하는 것을 권장합니다.
        self.temperature = temperature
        self.system_prompt = (
            "당신은 한국의 개인정보보호법(PIPA) 전문가이자 컴플라이언스 분석기입니다. "
            "주어진 개인정보 처리방침 텍스트를 분석하여, 제시된 JSON 스키마에 맞게 정확히 평가하세요. "
            "특히 모호한 표현(ambiguity), 법적 의무 누락(legal omission), "
            "그리고 서드파티 트래커(tracker) 언급 여부를 꼼꼼히 찾고 반드시 본문에서 증거(evidence span)를 원문 그대로 발췌해야 합니다."
        )

    @abc.abstractmethod
    def evaluate(self, policy_text: str) -> ComplianceEvaluation:
        """처리방침 텍스트를 입력받아 평가된 Pydantic 객체를 반환합니다."""
        pass


# -----------------------------------------------------------------------------
# 3. Real LLM Evaluator (실제 OpenAI 연동용 - 예시 구현)
# -----------------------------------------------------------------------------
class OpenAIPolicyEvaluator(BasePolicyEvaluator):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo", temperature: float = 0.0):
        super().__init__(temperature)
        self.model = model
        self.api_key = api_key
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)

    # 출력 형식 예시 (GPT-4가 스키마 자체를 반환하는 오류 방지용)
    _OUTPUT_EXAMPLE = '''{
  "has_mandatory_items": true,
  "mandatory_items_evidence": "수집 항목: 이메일, 전화번호 / 수집 목적: 서비스 제공",
  "ambiguity_detected": false,
  "ambiguity_evidence": null,
  "legal_omission_detected": true,
  "legal_omission_evidence": "개인정보 보호책임자 연락처 누락",
  "mentions_third_party_trackers": true,
  "tracker_evidence": "Google Analytics를 이용하여 사이트 이용 현황을 분석합니다."
}'''

    def evaluate(self, policy_text: str) -> ComplianceEvaluation:
        logging.info(f"LLM({self.model}) 분석 중...")
        # 텍스트 길이 제한 (토큰 절약)
        text_truncated = policy_text[:6000] if len(policy_text) > 6000 else policy_text
        if not text_truncated.strip():
            # 텍스트 없으면 Mock fallback
            return MockPolicyEvaluator().evaluate(policy_text)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=1024,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            self.system_prompt
                            + "\n\n다음 형식의 JSON 객체만 출력하세요 (설명 없이 JSON만):\n"
                            + self._OUTPUT_EXAMPLE
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"다음 개인정보 처리방침 텍스트를 분석하세요:\n\n{text_truncated}",
                    },
                ],
            )
            raw = response.choices[0].message.content
            return ComplianceEvaluation.model_validate_json(raw)
        except Exception as e:
            logging.warning(f"LLM API 오류, Mock으로 대체: {e}")
            return MockPolicyEvaluator().evaluate(policy_text)


# -----------------------------------------------------------------------------
# 4. Mock LLM Evaluator (더미 파이프라인 및 테스트용)
# -----------------------------------------------------------------------------
class MockPolicyEvaluator(BasePolicyEvaluator):
    def __init__(self, temperature: float = 0.0):
        super().__init__(temperature)
        
    def evaluate(self, policy_text: str) -> ComplianceEvaluation:
        """텍스트의 간단한 키워드 매칭을 통해 Mock JSON 결과를 반환하여 API 비용 없이 파이프라인을 테스트합니다."""
        logging.debug("Mock LLM을 사용하여 더미 분석을 수행합니다.")
        
        has_tracker = "트래커" in policy_text or "쿠키" in policy_text or "애널리틱스" in policy_text
        has_ambiguity = "필요 시" in policy_text or "경우에 따라" in policy_text
        has_omission = "책임자" not in policy_text
        
        return ComplianceEvaluation(
            has_mandatory_items=True,
            mandatory_items_evidence="수집항목: 이메일, 전화번호, 접속 IP",
            ambiguity_detected=has_ambiguity,
            ambiguity_evidence="필요 시 수집 항목이 변경될 수 있습니다." if has_ambiguity else None,
            legal_omission_detected=has_omission,
            legal_omission_evidence="개인정보 보호책임자의 성명 및 연락처가 본문에 기재되지 않음" if has_omission else None,
            mentions_third_party_trackers=has_tracker,
            tracker_evidence="서비스 이용 기록 분석을 위해 구글 애널리틱스 쿠키를 수집합니다." if has_tracker else None
        )

# -----------------------------------------------------------------------------
# Factory 함수
# -----------------------------------------------------------------------------
def get_evaluator(use_mock: bool = True, **kwargs) -> BasePolicyEvaluator:
    """설정에 따라 Mock 또는 Real LLM Evaluator를 반환합니다."""
    if use_mock:
        return MockPolicyEvaluator(temperature=kwargs.get("temperature", 0.0))

    api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수 또는 api_key 인수가 필요합니다.")
    return OpenAIPolicyEvaluator(
        api_key=api_key,
        model=kwargs.get("model", "gpt-4-turbo"),
        temperature=kwargs.get("temperature", 0.0),
    )
