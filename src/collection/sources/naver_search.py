from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Optional

_ENDPOINT = "https://openapi.naver.com/v1/search/webkr.json"

# 검색 결과에서 제외할 도메인 (포털/SNS/광고 등)
_EXCLUDE_DOMAINS = {
    # 포털 / 검색
    "naver.com", "google.com", "daum.net", "nate.com",
    # SNS / 미디어
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com",
    # 위키 / 백과
    "wikipedia.org", "namu.wiki",
    # 블로그 / 커뮤니티
    "blog.naver.com", "cafe.naver.com", "tistory.com", "brunch.co.kr",
    # 구인구직
    "jobkorea.co.kr", "saramin.co.kr", "wanted.co.kr",
    "catch.co.kr", "incruit.com", "jumpit.co.kr",
    # 스타트업 DB / 투자 정보 (기업 홈페이지 아님)
    "thevc.kr", "rocketpunch.com", "demoday.co.kr",
    "crunchbase.com", "linkedin.com", "startuprecipe.co.kr",
    # 정부 / 공공
    "go.kr", "or.kr", "data.go.kr", "work.go.kr",
    "kstartup.or.kr", "bizinfo.go.kr",
    # 뉴스
    "news.naver.com", "zdnet.co.kr", "techcrunch.com",
    "bloter.net", "platum.kr", "venturesquare.net",
}

_HTML_TAG = re.compile(r"<[^>]+>")


def _clean_link(link: str) -> Optional[str]:
    """검색 결과 링크에서 홈페이지 루트 URL 추출."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(link)
        domain = parsed.netloc.lower().removeprefix("www.")
        if any(ex in domain for ex in _EXCLUDE_DOMAINS):
            return None
        # 루트 URL만 반환
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None


class NaverURLDiscovery:
    """
    Naver 웹 검색 API를 사용해 기업 공식 홈페이지 URL을 탐색한다.

    API 키 발급: https://developers.naver.com
      → 내 애플리케이션 → 애플리케이션 등록 → 검색 API 선택
      → Client ID / Client Secret 발급 (무료, 일 25,000회)

    환경변수:
      NAVER_CLIENT_ID
      NAVER_CLIENT_SECRET
    """

    def __init__(self, cfg: dict):
        self.client_id = cfg.get("client_id") or os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = cfg.get("client_secret") or os.getenv("NAVER_CLIENT_SECRET", "")
        self.rate_limit_s = int(cfg.get("rate_limit_ms", 500)) / 1000

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Naver API 키가 없습니다. "
                "https://developers.naver.com 에서 발급 후 "
                "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수를 설정하세요."
            )

    def find_url(self, company_name: str) -> Optional[str]:
        """
        '{company_name} 공식 홈페이지' 를 검색해 첫 번째 유효 URL 반환.
        실패 시 None 반환.
        """
        query = urllib.parse.quote(f"{company_name} 공식 홈페이지")
        url = f"{_ENDPOINT}?query={query}&display=5&start=1"
        req = urllib.request.Request(
            url,
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            items = data.get("items", [])
            for item in items:
                link = _clean_link(item.get("link", ""))
                if link:
                    return link
        except Exception:
            pass
        return None

    def find_urls_batch(
        self,
        names: list[str],
        on_progress: Optional[callable] = None,
    ) -> dict[str, Optional[str]]:
        """
        기업명 리스트를 순서대로 검색해 {name: url} 딕셔너리 반환.
        rate_limit_ms 간격으로 요청.
        """
        results: dict[str, Optional[str]] = {}
        for i, name in enumerate(names):
            results[name] = self.find_url(name)
            if on_progress:
                on_progress(i + 1, len(names), name, results[name])
            time.sleep(self.rate_limit_s)
        return results
