"""Catch rate and False alarm rate per Finding type against Ground truth."""
from __future__ import annotations

import pandas as pd

# A Finding on a Benign trap is a false alarm only when it is about what makes the trap look wrong.
PAYMENT_TYPES = {"PAYMENT_AMOUNT_MISMATCH", "UNMATCHED_BANK_TXN", "DUPLICATE_PAYMENT", "PAID_NOT_IN_BANK"}
TRAP_TYPES = {
    "PARTIAL_PAYMENT": PAYMENT_TYPES,
    "BUNDLED_PAYMENT": PAYMENT_TYPES,
    "NON_INVOICE_TXN": {"UNMATCHED_BANK_TXN", "CIRCULAR_FLOW"},
    "ROUNDING_NOISE": {"TAX_CALC_ERROR", "AMOUNT_MISMATCH", "EXEMPT_ITEM_TAXED", "WRONG_TAX_RATE", "PAYMENT_AMOUNT_MISMATCH"},
    "CREDIT_NOTE": {"DUPLICATE_INVOICE", "MISSING_LEDGER_ENTRY", "WRONG_TAX_RATE", "TAX_CALC_ERROR", "WRONG_TAX_TYPE"},
    # Open purchase invoices past 180 days are Rule 37 Findings by design, so that type is not listed here.
    "LEGIT_OPEN_INVOICE": {"PAID_NOT_IN_BANK", "MISSING_LEDGER_ENTRY", "PAYMENT_AMOUNT_MISMATCH"},
}
# Types whose label names either record of a pair; catching the pair from either side counts.
PAIRED = {"DUPLICATE_INVOICE", "DUPLICATE_LEDGER_ENTRY", "DUPLICATE_PAYMENT", "CIRCULAR_FLOW", "PAN_LINKED_RING"}
# Filing labels the engine does not report as their own type.
NOT_REPORTED = {"ITC_ON_DUPLICATE_INVOICE"}


def _record_period(ds) -> dict[str, str]:
    """The Return period of every record a label can point at."""
    period: dict[str, str] = {}
    period.update(zip(ds.invoices["invoice_id"], ds.invoices["invoice_date"].dt.strftime("%Y-%m")))
    period.update(zip(ds.bank["txn_id"], ds.bank["txn_date"].dt.strftime("%Y-%m")))
    period.update(zip(ds.ledger["entry_id"], ds.ledger["posting_date"].dt.strftime("%Y-%m")))
    if ds.gstr2b is not None:
        period.update(zip(ds.gstr2b["line_id"], ds.gstr2b["return_period"].map(lambda p: f"{p[2:]}-{p[:2]}")))
    period.update({p: p for p in ds.filings["period"]})
    return period


def evaluate(ds, findings: list[dict], periods: tuple[str, ...] | None = None) -> list[dict]:
    """One row per Finding type: planted, caught, false alarms and the two rates. periods limits both sides."""
    where = _record_period(ds)
    labels = ds.labels[~ds.labels["issue_type"].isin(NOT_REPORTED)].copy()
    labels["period"] = labels["entity_id"].map(where)
    planted = labels[~labels["is_benign"]]
    traps = labels[labels["is_benign"]]
    reported = pd.DataFrame([{"finding_type": f["finding_type"], "entity_id": f["entity_id"], "period": f["period"],
                              "others": [r["id"] for r in f["record_refs"]]} for f in findings])
    # Compare like with like: a Finding belongs to the period of the record it is about, as its label does.
    reported["period"] = reported["entity_id"].map(where).fillna(reported["period"])
    rows = []
    for finding_type in sorted(set(planted["issue_type"]) | set(reported["finding_type"])):
        truth = planted[planted["issue_type"] == finding_type]
        got = reported[reported["finding_type"] == finding_type]
        if finding_type == "PAN_LINKED_RING":
            got = got.drop_duplicates("entity_id")
        elif periods is not None:
            truth = truth[truth["period"].isin(periods)]
            got = got[got["period"].isin(periods)]
        truth_ids = set(truth["entity_id"])
        related = set(truth["related_entity_id"].dropna()) if finding_type in PAIRED else set()
        got_ids = set(got["entity_id"])
        if finding_type in PAIRED:
            got_ids |= {i for others in got["others"] for i in others}
        caught = len(truth_ids & got_ids)
        false_alarms = int((~got["entity_id"].isin(truth_ids | related)).sum())
        trap_ids = set(traps.loc[traps["issue_type"].map(lambda trap: finding_type in TRAP_TYPES.get(trap, ())), "entity_id"])
        on_benign = int(got["entity_id"].isin(trap_ids).sum())
        rows.append({
            "finding_type": finding_type, "planted": len(truth_ids), "caught": caught, "reported": int(len(got)),
            "false_alarms": false_alarms, "on_benign_traps": on_benign,
            "catch_rate": caught / len(truth_ids) if truth_ids else None,
            "false_alarm_rate": false_alarms / len(got) if len(got) else None,
        })
    return rows
