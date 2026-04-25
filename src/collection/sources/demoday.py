from __future__ import annotations

import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from typing import Iterator

from ..schema import CompanyRecord


class _CardParser(HTMLParser):
    """Extracts (name, url) pairs from demoday.co.kr startup listing pages."""

    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._in_card = False
        self._cur: dict = {}
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if any(k in cls for k in ("startup-card", "company-card", "card-item")):
            self._in_card = True
            self._cur = {}
            self._depth = 0

        if self._in_card:
            self._depth += 1
            href = attrs_d.get("href", "")
            if tag == "a" and href.startswith("http") and "url" not in self._cur:
                self._cur["url"] = href

    def handle_data(self, data):
        text = data.strip()
        if self._in_card and text and "name" not in self._cur:
            self._cur["name"] = text

    def handle_endtag(self, tag):
        if self._in_card:
            self._depth -= 1
            if self._depth <= 0:
                if self._cur.get("url") and self._cur.get("name"):
                    self._items.append(dict(self._cur))
                self._in_card = False
                self._cur = {}

    @property
    def items(self) -> list[dict]:
        return self._items


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class DemoDayCollector:
    """
    Scrapes startup listings from demoday.co.kr.
    Uses stdlib only (no third-party HTTP client required).
    Enable with demoday.enabled: true in configs/base.yaml.
    """

    source_id = "demoday"

    def __init__(self, cfg: dict):
        self.base_url = cfg.get("base_url", "https://demoday.co.kr").rstrip("/")
        self.max_pages = int(cfg.get("max_pages", 10))
        self.rate_limit_s = int(cfg.get("rate_limit_ms", 3000)) / 1000
        self.timeout = 15

    def _fetch(self, page: int) -> str:
        url = f"{self.base_url}/startups?page={page}"
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def collect(self) -> Iterator[CompanyRecord]:
        seen: set[str] = set()
        counter = 0

        for page in range(1, self.max_pages + 1):
            try:
                html = self._fetch(page)
            except Exception as exc:
                print(f"  [demoday] page {page} failed: {exc}")
                break

            parser = _CardParser()
            parser.feed(html)

            if not parser.items:
                break

            for item in parser.items:
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                yield CompanyRecord(
                    company_id=f"DMD_{counter:04d}",
                    name=item["name"],
                    url=item["url"],
                    industry="other",
                    sources=[self.source_id],
                    collection_date=date.today(),
                )
                counter += 1

            time.sleep(self.rate_limit_s)
