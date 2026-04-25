import pandas as pd
from typing import List, Dict

class MismatchCalculator:
    """
    개인정보 처리방침의 고지(Disclosure)와 실제 네트워크 트래커 탐지(Practice) 간의 
    불일치(Mismatch)를 카테고리 단위로 세밀하게 계산하는 모듈입니다.
    """
    def __init__(self, categories: List[str] = None):
        if categories is None:
            # 기본 Taxonomy 카테고리
            self.categories = [
                "Analytics", "Advertising", "Session Replay", 
                "Social", "Fingerprinting", "Unknown"
            ]
        else:
            self.categories = categories

    def calculate_company_mismatch(self, company_id: str, detected_trackers: List[Dict], disclosed_categories: List[str]) -> Dict:
        """
        단일 기업에 대한 Mismatch를 카테고리별로 계산합니다.
        
        Args:
            company_id: 분석 대상 기업 ID
            detected_trackers: 네트워크 로깅을 통해 실제 탐지된 트래커 리스트 [{"category": "Analytics", ...}, ...]
            disclosed_categories: LLM 분석을 통해 처리방침 텍스트에서 명시적으로 고지된 것으로 파악된 카테고리 리스트 ["Analytics", ...]
            
        Returns:
            카테고리별 불일치 여부와 기업 단위 요약이 포함된 Dictionary
        """
        # 실제 탐지된 카테고리 Set 추출 (Practice)
        practice_set = set(t.get("category") for t in detected_trackers if t.get("category"))
        # 정책에 고지된 카테고리 Set 추출 (Disclosure)
        disclosure_set = set(disclosed_categories)
        
        result = {
            "company_id": company_id,
            "has_any_tracker": len(practice_set) > 0,
            "has_any_disclosure": len(disclosure_set) > 0,
            "categories": {}
        }
        
        under_disclosure_count = 0
        over_disclosure_count = 0
        composite_mismatch_count = 0
        
        # 카테고리 단위(Category-level) 1:1 비교
        for category in self.categories:
            in_practice = category in practice_set
            in_disclosure = category in disclosure_set
            
            # 1. Under-disclosure: 실제 트래킹은 관측되었으나 정책에 명시하지 않음
            under = in_practice and not in_disclosure
            # 2. Over-disclosure: 정책에는 명시했으나 실제 네트워크에서는 관측되지 않음
            over = in_disclosure and not in_practice
            # 3. Composite Mismatch: Under 또는 Over 중 하나라도 발생하는 구조적 불일치
            composite = under or over
            
            result["categories"][category] = {
                "practice": in_practice,
                "disclosure": in_disclosure,
                "under_disclosure": under,
                "over_disclosure": over,
                "composite_mismatch": composite
            }
            
            if under: under_disclosure_count += 1
            if over: over_disclosure_count += 1
            if composite: composite_mismatch_count += 1
            
        # 기업 단위(Company-level) 요약 지표 산출
        result["summary"] = {
            "under_disclosure": under_disclosure_count > 0,
            "over_disclosure": over_disclosure_count > 0,
            "composite_mismatch": composite_mismatch_count > 0,
            "under_count": under_disclosure_count,
            "over_count": over_disclosure_count,
            "composite_count": composite_mismatch_count
        }
        
        return result

    def aggregate_dataset(self, mismatch_results: List[Dict]) -> pd.DataFrame:
        """
        다수 기업의 Mismatch 분석 결과 리스트를 입력받아, 
        비율(Ratio) 계산 및 통계 분석이 용이한 Pandas DataFrame(Long format)으로 변환합니다.
        """
        rows = []
        for res in mismatch_results:
            cid = res["company_id"]
            for cat, data in res["categories"].items():
                rows.append({
                    "company_id": cid,
                    "category": cat,
                    "practice": data["practice"],
                    "disclosure": data["disclosure"],
                    "under_disclosure": data["under_disclosure"],
                    "over_disclosure": data["over_disclosure"],
                    "composite_mismatch": data["composite_mismatch"]
                })
        return pd.DataFrame(rows)
