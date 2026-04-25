from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date
from typing import Iterator

from ..schema import CompanyRecord

_ENDPOINT = "https://apis.data.go.kr/1090000/VentureFirmInfoService/getVentureFirmInfo"

_INDUSTRY_MAP = {
    "정보통신": "saas",
    "바이오": "healthtech",
    "제조": "other",
    "유통": "ecommerce",
    "금융": "fintech",
    "교육": "edtech",
    "의료": "healthtech",
    "물류": "logistics",
    "미디어": "media",
    "게임": "gaming",
    "부동산": "proptech",
    "음식": "foodtech",
    "모빌리티": "mobility",
}


def _map_industry(raw: str) -> str:
    for k, v in _INDUSTRY_MAP.items():
        if k in (raw or ""):
            return v
    return "other"


class KStartupCollector:
    """
    Fetches certified venture company list from data.go.kr
    (벤처기업확인기관 정보 서비스 — 공공데이터포털 API).

    API key: https://www.data.go.kr → 인증키 발급 → 벤처기업확인기관정보
    Set kstartup.api_key in configs/base.yaml or pass via environment variable
    KSTARTUP_API_KEY before enabling this source.
    """

    source_id = "kstartup"

    def __init__(self, cfg: dict):
        import os

        self.api_key = cfg.get("api_key") or os.getenv("KSTARTUP_API_KEY", "")
        self.max_results = int(cfg.get("max_results", 200))
        self.endpoint = cfg.get("service_url", _ENDPOINT)
        self.timeout = int(cfg.get("timeout_s", 15))

    def collect(self) -> Iterator[CompanyRecord]:
        if not self.api_key:
            raise ValueError(
                "kstartup.api_key is required. "
                "Obtain from https://www.data.go.kr and set KSTARTUP_API_KEY env var."
            )

        page, page_size, collected = 1, 100, 0

        while collected < self.max_results:
            params = urllib.parse.urlencode(
                {
                    "serviceKey": self.api_key,
                    "pageNo": page,
                    "numOfRows": min(page_size, self.max_results - collected),
                    "type": "json",
                }
            )
            req = urllib.request.Request(
                f"{self.endpoint}?{params}",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())

            items = data.get("response", {}).get("body", {}).get("items", [])
            if not items:
                break

            for i, item in enumerate(items):
                homepage = (item.get("homepageUrl") or "").strip()
                if not homepage:
                    continue
                yield CompanyRecord(
                    company_id=f"KST_{(collected + i):04d}",
                    name=(item.get("ventureFirmName") or "").strip(),
                    url=homepage,
                    industry=_map_industry(item.get("mainBusinessType", "")),
                    sources=[self.source_id],
                    collection_date=date.today(),
                )

            collected += len(items)
            if len(items) < page_size:
                break
            page += 1
