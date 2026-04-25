from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

from ..schema import CompanyRecord

# ── URL 추출 ──────────────────────────────────────────────────────────────────
_ENG_IN_PAREN = re.compile(r"\(([A-Za-z][A-Za-z0-9\s\-.,'/]*?)\)")
_CORP_SUFFIX = re.compile(
    r"\b(co\.?,?|ltd\.?|corp\.?|inc\.?|llc\.?|plc\.?|gmbh)\b", re.IGNORECASE
)
_NON_ALNUM = re.compile(r"[^a-z0-9]")

# 기업명에서 주식회사 등 법인격 표시 제거
_CORP_KOR = re.compile(r"주식회사|㈜|\(주\)|유한회사|\(유\)|합명회사|합자회사")


def _extract_url(raw_name: str) -> str:
    """
    영문 도메인 후보를 추출한다.
    1순위: 괄호 안 영문 상호 → 'https://www.{domain}.co.kr'
    2순위: 이름 자체가 영문인 경우
    추출 불가 시 "" 반환 (Naver 탐색 대상으로 분류됨)
    """
    # 1순위: 괄호 속 영문
    m = _ENG_IN_PAREN.search(raw_name)
    if m:
        eng = _CORP_SUFFIX.sub("", m.group(1)).strip()
        domain = _NON_ALNUM.sub("", eng.lower())
        if len(domain) >= 3:
            return f"https://www.{domain}.co.kr"

    # 2순위: 법인격 제거 후 영문만 남는 경우
    cleaned = _CORP_KOR.sub("", raw_name).strip()
    if re.fullmatch(r"[A-Za-z0-9\s\-_.]+", cleaned):
        domain = _NON_ALNUM.sub("", cleaned.lower())
        if len(domain) >= 3:
            return f"https://www.{domain}.co.kr"

    return ""  # URL 미확인 → discover-urls 대상


# ── 업종 매핑 ──────────────────────────────────────────────────────────────────
def _map_industry(product: str, sector_name: str) -> str:
    text = f"{product or ''} {sector_name or ''}".lower()
    if any(k in text for k in ["금융", "결제", "핀테크", "투자", "보험", "대출", "크레딧"]):
        return "fintech"
    if any(k in text for k in ["교육", "학습", "이러닝", "e-learning", "에듀", "학원", "학교"]):
        return "edtech"
    if any(k in text for k in ["의료", "헬스", "의약", "진단", "바이오", "의학", "병원", "케어"]):
        return "healthtech"
    if any(k in text for k in ["게임"]):
        return "gaming"
    if any(k in text for k in ["미디어", "콘텐츠", "영상", "음악", "방송", "웹툰", "출판", "엔터"]):
        return "media"
    if any(k in text for k in ["쇼핑", "커머스", "이커머스", "몰", "리테일", "판매", "유통"]):
        return "ecommerce"
    if any(k in text for k in ["물류", "배송", "운송", "택배", "화물", "로지스틱"]):
        return "logistics"
    if any(k in text for k in ["부동산", "임대", "건설", "건축"]):
        return "proptech"
    if any(k in text for k in ["식품", "음식", "배달", "푸드", "외식"]):
        return "foodtech"
    return "saas"


# ── Collector ─────────────────────────────────────────────────────────────────
class MSMECollector:
    """
    중소벤처기업부 벤처기업명단 CSV에서 IT/SW 기업을 수집한다.
    영문명이 있는 기업은 도메인 후보 URL을 자동 생성하고,
    한글명만인 기업은 url=""로 설정해 discover-urls 대상으로 남긴다.
    """

    source_id = "msme"

    def __init__(self, cfg: dict):
        self.csv_path = Path(
            cfg.get("csv_path", "data/external/msme_ventures_20250228.csv")
        )
        self.sector_filter: list[str] = cfg.get(
            "sector_filter", ["정보처리S/W"]
        )
        self.max_results = int(cfg.get("max_results", 2000))

    def collect(self) -> Iterator[CompanyRecord]:
        df = pd.read_csv(self.csv_path, encoding="utf-8-sig")

        if self.sector_filter:
            df = df[df["업종분류(기보)"].isin(self.sector_filter)]

        # 벤처유효종료일이 오늘 이후인 기업만 (현재 유효한 인증)
        today_str = date.today().strftime("%Y-%m-%d")
        if "벤처유효종료일" in df.columns:
            df = df[df["벤처유효종료일"] >= today_str]

        df = df.head(self.max_results)

        for i, row in df.iterrows():
            raw_name: str = str(row.get("업체명", "")).strip()
            product: str = str(row.get("주생산품", ""))
            sector_name: str = str(row.get("업종명(11차)", ""))

            # 벤처확인 시작년도로 founding_year 근사
            start_str = str(row.get("벤처유효시작일", ""))
            founding_year: Optional[int] = None
            if start_str and len(start_str) >= 4 and start_str[:4].isdigit():
                founding_year = int(start_str[:4])

            yield CompanyRecord(
                company_id=f"MSM_{i:05d}",
                name=_CORP_KOR.sub("", raw_name).strip(),
                url=_extract_url(raw_name),
                industry=_map_industry(product, sector_name),
                founding_year=founding_year,
                employee_range=None,
                sources=[self.source_id],
                collection_date=date.today(),
            )

    @property
    def pending_count(self) -> int:
        """URL 미확인 기업 수 (참고용)."""
        return sum(1 for r in self.collect() if not r.url)
