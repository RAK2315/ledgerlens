"""Write and cache a Draft for every Finding of a period, so the demo needs no network.

Run from the repo root: backend\.venv\Scripts\python -m app.drafts.precache --period 2025-09 (with --app-dir style: cd backend first).
"""
from __future__ import annotations

import argparse
import time
from collections import Counter

from .. import db, settings
from ..engine import analyse
from . import llm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default=settings.DEFAULT_PERIOD)
    args = parser.parse_args()
    settings.load_env_file()
    result, _ = analyse.analysis()
    names = analyse.books().parties["party_name"].to_dict()
    findings = [f for f in result.findings if f["period"] == args.period]
    sources: Counter = Counter()
    for n, finding in enumerate(findings, start=1):
        for attempt in range(4):
            draft = llm.write(finding, names.get(finding["party_id"]))
            if draft["source"] != "template" or settings.llm_mode() != "live":
                break
            time.sleep(3 * (attempt + 1))
        sources[draft["source"]] += 1
        print(f"{n}/{len(findings)} {draft['source']:<8} {finding['finding_type']:<24} {draft['subject'][:70]}", flush=True)
    print(dict(sources), "cache:", settings.cache_dir() / "drafts", db.now())


if __name__ == "__main__":
    main()
