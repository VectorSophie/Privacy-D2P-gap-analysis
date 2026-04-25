from .collector import MultiSourceCollector, build_collector
from .deduplicator import deduplicate
from .schema import CompanyRecord, CrawlStatus, MismatchLabel, PipelineRecord

__all__ = [
    "CompanyRecord",
    "PipelineRecord",
    "CrawlStatus",
    "MismatchLabel",
    "MultiSourceCollector",
    "build_collector",
    "deduplicate",
]
