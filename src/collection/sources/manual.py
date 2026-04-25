from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterator

from ..schema import CompanyRecord


class ManualCSVCollector:
    """Loads curated companies from a hand-maintained CSV seed file."""

    source_id = "manual"

    def __init__(self, cfg: dict):
        self.csv_path = Path(cfg.get("csv_path", "data/external/seed_companies.csv"))

    def collect(self) -> Iterator[CompanyRecord]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Seed CSV not found: {self.csv_path}")

        with open(self.csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                yield CompanyRecord(
                    company_id=f"MAN_{i:04d}",
                    name=row["name"].strip(),
                    url=row["url"].strip(),
                    industry=(row.get("industry") or "other").strip() or "other",
                    founding_year=int(row["founding_year"]) if row.get("founding_year", "").strip() else None,
                    employee_range=row.get("employee_range", "").strip() or None,
                    sources=[self.source_id],
                    collection_date=date.today(),
                )
