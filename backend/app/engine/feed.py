"""Example lines for the live feed of a Run: real records and results of the month, a few per stage."""
from __future__ import annotations

from .findings import rupees

PER_STAGE = 6
IMPACT_WORDS = {"itc_at_risk": "ITC at risk", "itc_found": "ITC found", "excess_tax": "excess tax", "short_tax": "short tax",
                "unaccounted_payment": "unaccounted", "open_payable": "open payable"}
# The order matches are shown in: the plain ones first, then the ones that needed more than an exact number.
MATCH_ORDER = (("booking", "exact"), ("payment", "exact"), ("payment", "normalised"), ("payment", "fuzzy"), ("payment", "model"),
               ("payment", "one_to_many"), ("supplier_filing", "exact"), ("supplier_filing", "normalised"))


def _spread(frame, count: int):
    """Rows taken evenly across the frame, so the examples are not all from the first day."""
    step = max(1, len(frame) // count)
    return frame.iloc[::step].head(count)


def _month(frame, column: str, period: str):
    return frame[frame[column].dt.strftime("%Y-%m") == period]


def _match_line(m: dict) -> str:
    invoices, rights = ", ".join(m["invoice_ids"]), ", ".join(m["right_ids"])
    why = m["reasons"][0] if m["reasons"] else ""
    if m["layer"] == "one_to_many":
        return f"{rights} against {invoices}. {why}"
    verb = {"booking": "booked as", "payment": "paid by", "supplier_filing": "in GSTR-2B as"}[m["kind"]]
    return f"{invoices} {verb} {rights}. {why}"


def _largest(findings: list[dict], count: int = PER_STAGE) -> list[dict]:
    return sorted(findings, key=lambda f: -f["impact_paise"])[:count]


def items(b, period: str, matches: list[dict], findings: list[dict]) -> dict[str, list[str]]:
    """Up to PER_STAGE lines for each stage, every one taken from the month's records, Matches or Findings."""
    inv, bank, ledger = _month(b.inv, "invoice_date", period), _month(b.bank, "txn_date", period), _month(b.ledger, "posting_date", period)
    names = dict(zip(b.inv["party_id"], b.inv["party_name"]))

    read = [f"{r.invoice_id}  {r.party_name}  {rupees(r.invoice_total_paise)}" for r in _spread(inv, 2).itertuples()]
    read += [f"{r.entry_id}  {r.narration}" for r in _spread(ledger, 2).itertuples()]
    read += [f"{r.txn_id}  {r.narration}" for r in _spread(bank, 2).itertuples()]

    renamed = [m for m in matches if m["kind"] == "supplier_filing" and m["layer"] == "normalised" and m["reasons"]]
    clean = [f"{m['invoice_id']}  {m['reasons'][0]}" for m in renamed[:3]]
    traced = bank[bank["resolved_party_id"].notna()]
    traced = traced[[str(name).lower() != str(names.get(party, "")).lower() for name, party in zip(traced["counterparty_name"], traced["resolved_party_id"])]]
    clean += [f"{r.txn_id}  {r.counterparty_name} is {names.get(r.resolved_party_id, r.resolved_party_id)}" for r in _spread(traced, PER_STAGE - len(clean)).itertuples()]

    settled = [m for m in matches if m["right_ids"]]
    first = {}
    for m in settled:
        first.setdefault((m["kind"], m["layer"]), m)
    match = [_match_line(first[key]) for key in MATCH_ORDER if key in first][:PER_STAGE]

    checks = [f for f in findings if f["category"] != "anomaly"]
    by_category = {}
    for f in _largest(checks, len(checks)):
        by_category.setdefault(f["category"], f)
    check = [f["title"] for f in _largest(list(by_category.values()))]
    check += [f["title"] for f in _largest(checks, PER_STAGE * 2) if f["title"] not in check][: PER_STAGE - len(check)]

    anomalies = [f["title"] for f in _largest([f for f in findings if f["category"] == "anomaly"])]
    priced = [f for kind, count in (("itc_at_risk", 3), ("itc_found", 1), ("excess_tax", 1), ("short_tax", 1))
              for f in _largest([f for f in findings if f["impact_type"] == kind], count)]
    money = [f"{rupees(f['impact_paise'])} {IMPACT_WORDS[f['impact_type']]}  {f['entity_id']}" for f in priced]
    steps = {}
    for f in _largest(findings, len(findings)):
        steps.setdefault(f["what_to_do"], f)
    explain = [f"{f['entity_id']}  {step}" for step, f in list(steps.items())[:PER_STAGE]]
    return {"read": read, "clean": clean, "match": match, "check": check, "anomalies": anomalies, "money": money, "explain": explain}
