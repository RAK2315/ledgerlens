"""One Run: reconcile a Return period, stream its stages, store Matches, Findings and the base money figures."""
from __future__ import annotations

import json
import threading
import time
import traceback
from collections import Counter

from .. import db, settings
from . import analyse, feed, money, records
from .findings import rupees

COMPANY = {"name": "Sharma Traders Pvt Ltd", "gstin": "07AAACS1234F1ZU"}


class RunInProgress(Exception):
    """A Run for this Return period is already running."""


def load_demo() -> dict:
    """Load the dataset into the store once; later calls return the stored dataset."""
    ds = analyse.dataset()
    existing = db.dataset_by_sha(ds.sha256)
    if existing is None:
        dataset_id = f"ds_{ds.sha256[:8]}"
        b = analyse.books()
        db.save_dataset({"id": dataset_id, "name": "Demo company books, FY 2025-26", "company_name": COMPANY["name"], "company_gstin": COMPANY["gstin"],
                         "source_sha256": ds.sha256, "loaded_at": db.now()}, records.build(dataset_id, b, ds.answer_key))
    else:
        dataset_id = existing["id"]
    return {"dataset_id": dataset_id, "company": COMPANY, "periods": db.periods(dataset_id), "counts": db.record_counts(dataset_id)}


def start(dataset_id: str, period: str) -> str:
    if db.running_run(period):
        raise RunInProgress(period)
    run_id = db.create_run(dataset_id, period)
    threading.Thread(target=execute, args=(run_id, period), daemon=True).start()
    return run_id


def execute(run_id: str, period: str) -> None:
    stage = "read"
    try:
        db.update_run(run_id, status="running", started_at=db.now())
        db.add_event(run_id, "read", "started", "Reading invoices, ledger, bank statement and GSTR-2B")
        result, cached = analyse.analysis()
        b = analyse.books()
        pause = settings.stage_delay()
        findings = [f for f in result.findings if f["period"] == period]
        matches = [m for m in result.matches if m["period"] == period]
        base = money.base(b, period, result.matches)
        summary = money.summarise(base, [dict(f, status="open") for f in findings])
        categories = Counter(f["category"] for f in findings)
        month = lambda frame, column: int((frame[column].dt.strftime("%Y-%m") == period).sum())
        counts = base["match_counts"]
        messages = {
            "read": f"{base['invoice_count']:,} invoices, {month(b.ledger, 'posting_date'):,} ledger entries, {month(b.bank, 'txn_date'):,} bank lines and GSTR-2B for {period}",
            "clean": "Invoice numbers and Party names cleaned, bank lines traced to Parties",
            "match": f"{counts['auto']:,} matched automatically, {counts['review']} for review, {counts['one_to_many']} one-to-many",
            "check": f"{categories['tax'] + categories['duplicate'] + categories['missing'] + categories['matching'] + categories['filing']} Findings from tax, duplicate and missing checks",
            "anomalies": f"{categories['anomaly']} Anomalies, each with a reason",
            "money": f"ITC at risk {rupees(summary['itc_at_risk_paise'])}, ITC found {rupees(summary['itc_found_paise'])}",
            "explain": f"{len(findings)} Findings explained with evidence",
        }
        starts = {"clean": "Cleaning invoice numbers and Party names", "match": "Matching invoices to bookings, payments and Supplier filings",
                  "check": "Checking rates, tax type, arithmetic, duplicates and Rule 37", "anomalies": "Looking for unusual invoices and Supplier rings",
                  "money": "Working out ITC at risk, ITC found and Net payable", "explain": "Writing the reason and next step for each Finding"}
        examples = feed.items(b, period, matches, findings)
        for stage in analyse.STAGES:
            if stage != "read":
                db.add_event(run_id, stage, "started", starts[stage])
            if stage == "explain":
                db.save_results(run_id, matches, findings)
            gap = pause / (len(examples[stage]) + 1)
            for line in examples[stage]:
                time.sleep(gap)
                db.add_item(run_id, stage, line)
            time.sleep(gap)
            db.add_event(run_id, stage, "done", messages[stage])
        db.update_run(run_id, status="done", finished_at=db.now(), summary_json=json.dumps(base))
    except Exception as error:  # the Run must end in a terminal state whatever went wrong
        traceback.print_exc()
        db.add_event(run_id, stage, "failed", str(error))
        db.update_run(run_id, status="failed", finished_at=db.now(), error=str(error))


def summary(run: dict) -> dict:
    """Headline numbers for a Run, from its stored base figures and the current Finding statuses."""
    return money.summarise(json.loads(run["summary_json"]), db.findings_of(run["id"]))
