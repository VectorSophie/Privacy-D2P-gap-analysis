from __future__ import annotations

from .deduplicator import deduplicate
from .schema import CompanyRecord


class MultiSourceCollector:
    def __init__(self, collectors: list):
        self.collectors = collectors

    def collect_all(self) -> list[CompanyRecord]:
        raw: list[CompanyRecord] = []
        for c in self.collectors:
            before = len(raw)
            try:
                raw.extend(c.collect())
                print(f"  [{c.source_id}] +{len(raw) - before} records (total {len(raw)})")
            except Exception as exc:
                print(f"  [{c.source_id}] SKIPPED — {exc}")
        return raw


def build_collector(cfg: dict) -> tuple[MultiSourceCollector, float]:
    """configs/base.yaml의 collection 섹션을 읽어 활성화된 소스 컬렉터를 생성합니다.

    소스 우선순위: manual → msme → kstartup → demoday (설정 순서).
    각 소스는 sources.<name>.enabled: true 일 때만 로드됩니다.

    Returns:
        (MultiSourceCollector, name_dedup_threshold) 튜플.
        threshold는 이름 유사도 기반 중복 판정 기준값 (기본 0.88).
    """
    from .sources.demoday import DemoDayCollector
    from .sources.kstartup import KStartupCollector
    from .sources.manual import ManualCSVCollector

    col_cfg = cfg.get("collection", {})
    src_cfg = col_cfg.get("sources", {})
    collectors: list = []

    if src_cfg.get("manual", {}).get("enabled", True):
        collectors.append(ManualCSVCollector(src_cfg.get("manual", {})))
    if src_cfg.get("msme", {}).get("enabled", False):
        from .sources.msme import MSMECollector
        collectors.append(MSMECollector(src_cfg["msme"]))
    if src_cfg.get("kstartup", {}).get("enabled", False):
        collectors.append(KStartupCollector(src_cfg["kstartup"]))
    if src_cfg.get("demoday", {}).get("enabled", False):
        collectors.append(DemoDayCollector(src_cfg["demoday"]))

    threshold = float(col_cfg.get("dedup_name_threshold", 0.88))
    return MultiSourceCollector(collectors), threshold
