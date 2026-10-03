"""Run every check over the whole dataset once and keep the result. A Run reads its Return period from this."""
from __future__ import annotations

import hashlib
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from .. import settings
from . import anomalies, duplicates, filing, matching, rings, rule37, supplier_filing, tax_rules
from .findings import Books

STAGES = ("read", "clean", "match", "check", "anomalies", "money", "explain")
STAGE_LABELS = {"read": "Reading records", "clean": "Cleaning up", "match": "Matching", "check": "Checking tax",
                "anomalies": "Looking for anomalies", "money": "Working out the money", "explain": "Writing explanations"}
Progress = Callable[[str, str, str], None]


@dataclass
class Analysis:
    findings: list[dict]
    matches: list[dict]
    counts: dict[str, int]


_lock = threading.Lock()
_state: dict = {}


def dataset():
    """The ML Dataset, loaded once per process."""
    if "ds" not in _state:
        from ledgerlens_ml import load_dataset
        path = settings.dataset_path()
        kwargs = {"expected_sha256": None} if path else {}
        _state["ds"] = load_dataset(path, settings.derived_dir(), **kwargs)
    return _state["ds"]


def books() -> Books:
    if "books" not in _state:
        from ledgerlens_ml import resolve_bank
        ds = dataset()
        if ds.gstr2b is None:
            raise RuntimeError("GSTR-2B lines are missing; run python -m ledgerlens_ml augment")
        bank = resolve_bank(ds.bank, ds.parties, ds.invoices)
        _state["books"] = Books(
            inv=ds.invoices.set_index("invoice_id", drop=False), ledger=ds.ledger.set_index("entry_id", drop=False),
            bank=bank.set_index("txn_id", drop=False), parties=ds.parties.set_index("party_id", drop=False),
            lines=ds.gstr2b.set_index("line_id", drop=False), tax_rates=ds.tax_rates, filings=ds.filings,
            as_of=pd.Timestamp(ds.invoices["invoice_date"].max()))
    return _state["books"]


def reset() -> None:
    """Forget everything loaded. Tests use this when they switch datasets."""
    _state.clear()


def _cache_file() -> Path:
    """One file per dataset, model pair and engine source, so stale results are never reused."""
    from ledgerlens_ml import load_artifact
    digest = hashlib.sha256(dataset().sha256.encode())
    for kind in ("booking", "payment"):
        digest.update(load_artifact(kind)["trained_at"].encode())
    for source in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(source.read_bytes())
    return settings.cache_dir() / f"analysis_{digest.hexdigest()[:16]}.pkl"


def _compute(progress: Progress) -> Analysis:
    from ledgerlens_ml import score_pairs, train_aggregates
    progress("read", "started", "Loading invoices, ledger, bank statement and GSTR-2B")
    ds, b = dataset(), books()
    progress("read", "done", f"{len(b.inv):,} invoices, {len(b.ledger):,} ledger entries, {len(b.bank):,} bank lines, {len(b.lines):,} GSTR-2B lines")
    progress("clean", "started", "Cleaning invoice numbers and Party names")
    resolved = int(b.bank["resolved_party_id"].notna().sum())
    progress("clean", "done", f"{resolved:,} bank lines traced to a Party")

    progress("match", "started", "Matching invoices to bookings, payments and Supplier filings")
    findings: list[dict] = []
    duplicate_findings = duplicates.check(b)
    booking_findings, booking_matches = matching.booking(b, score_pairs("booking", ds))
    payment_findings, payment_matches, paid = matching.payments(b, score_pairs("payment", ds))
    filing_findings, filing_matches = supplier_filing.check(b, {f["entity_id"] for f in duplicate_findings})
    matches = booking_matches + payment_matches + filing_matches
    progress("match", "done", f"{sum(m['band'] == 'auto' for m in matches):,} matched with high Confidence")

    progress("check", "started", "Checking rates, tax type, arithmetic, duplicates and Rule 37")
    findings += tax_rules.check(b) + duplicate_findings + booking_findings + payment_findings + filing_findings
    skip = {f["entity_id"] for f in duplicate_findings} | {f["invoice_id"] for f in payment_findings if f["finding_type"] == "PAID_NOT_IN_BANK"}
    findings += rule37.check(b, paid, skip) + filing.check(b)
    progress("check", "done", f"{len(findings):,} Findings so far")

    progress("anomalies", "started", "Looking for unusual invoices and Supplier rings")
    unusual = anomalies.check(b, train_aggregates(ds.invoices)) + rings.check(b)
    findings += unusual
    progress("anomalies", "done", f"{len(unusual):,} Anomalies with reasons")
    return Analysis(findings=findings, matches=matches, counts={"invoices": len(b.inv), "ledger": len(b.ledger), "bank": len(b.bank), "lines": len(b.lines)})


def analysis(progress: Progress | None = None) -> tuple[Analysis, bool]:
    """The whole-year result and whether it came from the cache."""
    progress = progress or (lambda stage, status, message: None)
    with _lock:
        if "analysis" in _state:
            return _state["analysis"], True
        path = _cache_file()
        if path.exists():
            _state["analysis"] = pickle.loads(path.read_bytes())
            return _state["analysis"], True
        result = _compute(progress)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(result))
        _state["analysis"] = result
        return result, False
