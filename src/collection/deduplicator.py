from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlparse

from .schema import CompanyRecord

# Strips legal entity suffixes before name comparison
_CORP_RE = re.compile(
    r"[\s]*(주식회사|유한회사|\(주\)|\(유\)|inc\.?|corp\.?|co\.?|ltd\.?)[\s]*",
    flags=re.IGNORECASE,
)


def _norm_url(url: str) -> Optional[str]:
    """URL을 소문자·www 제거·후행 슬래시 제거한 정규화 문자열로 변환합니다.
    빈 URL이거나 파싱 실패 시 None을 반환하며, 호출부에서 URL 중복 판정을 건너뜁니다."""
    if not url or url.strip() == "":
        return None
    try:
        p = urlparse(url.lower().strip())
        host = p.netloc.removeprefix("www.")
        return host + p.path.rstrip("/") or None
    except Exception:
        return None


def _norm_name(name: str) -> str:
    name = name.lower().strip()
    name = _CORP_RE.sub("", name)
    return re.sub(r"\s+", "", name)


def _similar(a: str, b: str, threshold: float) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold


def deduplicate(
    records: list[CompanyRecord],
    name_threshold: float = 0.88,
) -> list[CompanyRecord]:
    """
    Two-pass deduplication:
      1. Exact normalized-URL match (primary)
      2. Name similarity above threshold (fallback)

    On duplicate: merges source lists into the first-seen record.
    Returns new list; original records are not mutated.
    """
    seen_urls: dict[str, int] = {}
    norm_names: list[str] = []
    result: list[CompanyRecord] = []

    for rec in records:
        nu = _norm_url(rec.url)   # None when url is empty
        nn = _norm_name(rec.name)

        # URL 기반 중복 — 빈 URL은 URL 중복 판정에서 제외
        if nu and nu in seen_urls:
            existing = result[seen_urls[nu]]
            existing.sources = list(dict.fromkeys(existing.sources + rec.sources))
            continue

        # 이름 기반 중복
        name_dup_idx = next(
            (i for i, en in enumerate(norm_names) if _similar(nn, en, name_threshold)),
            None,
        )
        if name_dup_idx is not None:
            existing = result[name_dup_idx]
            existing.sources = list(dict.fromkeys(existing.sources + rec.sources))
            continue

        if nu:  # 비어 있지 않은 URL만 seen_urls에 등록
            seen_urls[nu] = len(result)
        norm_names.append(nn)
        result.append(rec.model_copy())

    return result
