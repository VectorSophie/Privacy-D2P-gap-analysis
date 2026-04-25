from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CrawlStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ROBOTS_BLOCKED = "robots_blocked"
    NO_POLICY = "no_policy"


class MismatchLabel(str, Enum):
    NONE = "none"
    UNDER = "under_disclosure"
    OVER = "over_disclosure"
    COMPOSITE = "composite_mismatch"


class CompanyRecord(BaseModel):
    """Output of collection stage — input to crawling stage."""

    company_id: str
    name: str
    url: str
    industry: str = "other"
    founding_year: Optional[int] = None
    employee_range: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    collection_date: date = Field(default_factory=date.today)

    @field_validator("url")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return ""  # URL 미확인 — discover-urls 대상
        if not v.startswith(("http://", "https://")):
            return "https://" + v
        return v

    def to_row(self) -> dict:
        """Flat dict suitable for pandas / CSV output."""
        return {
            "company_id": self.company_id,
            "name": self.name,
            "url": self.url,
            "industry": self.industry,
            "founding_year": self.founding_year,
            "employee_range": self.employee_range,
            "sources": "|".join(self.sources),
            "collection_date": str(self.collection_date),
        }


class PipelineRecord(CompanyRecord):
    """Extends CompanyRecord with per-stage execution state for the full pipeline."""

    crawl_status: CrawlStatus = CrawlStatus.PENDING
    policy_url: Optional[str] = None
    policy_text_length: Optional[int] = None
    tracker_count: Optional[int] = None
    disclosure_score: Optional[float] = None  # 0.0–1.0
    mismatch_label: MismatchLabel = MismatchLabel.NONE
    manual_verified: bool = False
