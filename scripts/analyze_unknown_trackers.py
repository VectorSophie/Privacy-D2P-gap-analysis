"""Analyze Unknown Third-party domains to guide TRACKER_DB expansion.

Reads data/interim/trackers.json and prints the top-N unknown domains
by frequency, sorted by occurrence count across all sites.

Usage:
    uv run python scripts/analyze_unknown_trackers.py --top 50
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=50, help="Number of top domains to show")
    parser.add_argument("--min-sites", type=int, default=2, help="Minimum distinct sites")
    args = parser.parse_args()

    tracker_path = Path("data/interim/trackers.json")
    if not tracker_path.exists():
        raise FileNotFoundError("trackers.json not found — run detect-trackers first")

    with open(tracker_path, encoding="utf-8") as f:
        tracker_map = json.load(f)

    domain_counter: Counter = Counter()
    domain_sites: dict[str, set] = {}

    for company_id, trackers in tracker_map.items():
        for t in trackers:
            if t.get("category") == "Unknown":
                domain = t.get("domain", "")
                if domain:
                    domain_counter[domain] += 1
                    domain_sites.setdefault(domain, set()).add(company_id)

    print(f"\nTotal unique unknown domains: {len(domain_counter)}")
    print(f"Showing top {args.top} (min {args.min_sites} distinct sites):\n")
    print(f"{'Domain':<45} {'Sites':>6} {'Requests':>9}")
    print("-" * 65)

    shown = 0
    for domain, count in domain_counter.most_common():
        sites = len(domain_sites[domain])
        if sites < args.min_sites:
            continue
        print(f"{domain:<45} {sites:>6} {count:>9}")
        shown += 1
        if shown >= args.top:
            break

    total_unknown = sum(domain_counter.values())
    print(f"\nTotal unknown requests: {total_unknown}")


if __name__ == "__main__":
    main()
