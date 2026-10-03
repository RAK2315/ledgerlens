"""Shared building blocks for Findings: the indexed books, record views, diffs and the Finding dict."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .labels import META

COMPANY_STATE = 7

INVOICE_FIELDS = ["invoice_type", "doc_type", "invoice_date", "party_name", "party_gstin", "place_of_supply", "hsn_sac", "category",
                  "taxable_value_paise", "tax_rate_pct", "cgst_paise", "sgst_paise", "igst_paise", "total_tax_paise", "invoice_total_paise"]
LEDGER_FIELDS = ["voucher_type", "posting_date", "party_name", "invoice_ref", "taxable_amount_paise", "total_tax_paise", "total_amount_paise", "narration", "entered_by"]
BANK_FIELDS = ["txn_date", "direction", "amount_paise", "counterparty_name", "payment_mode", "utr", "narration"]
LINE_FIELDS = ["gstin_supplier", "trade_name", "invoice_number", "invoice_date", "return_period", "taxable_value_paise", "rate",
               "cgst_paise", "sgst_paise", "igst_paise", "invoice_value_paise"]
FIELD_LABELS = {
    "invoice_type": "Kind", "doc_type": "Document", "invoice_date": "Invoice date", "party_name": "Party", "party_gstin": "GSTIN",
    "place_of_supply": "Place of supply", "hsn_sac": "HSN code", "category": "Item", "taxable_value_paise": "Taxable value",
    "tax_rate_pct": "GST rate", "cgst_paise": "CGST", "sgst_paise": "SGST", "igst_paise": "IGST", "total_tax_paise": "Total tax",
    "invoice_total_paise": "Invoice total", "voucher_type": "Voucher", "posting_date": "Posting date", "invoice_ref": "Invoice reference",
    "taxable_amount_paise": "Taxable value", "total_amount_paise": "Total", "narration": "Narration", "entered_by": "Entered by",
    "txn_date": "Date", "direction": "Direction", "amount_paise": "Amount", "counterparty_name": "Counterparty", "payment_mode": "Mode",
    "utr": "UTR", "gstin_supplier": "Supplier GSTIN", "trade_name": "Supplier", "invoice_number": "Invoice number",
    "return_period": "Return period", "rate": "GST rate", "invoice_value_paise": "Invoice total",
}


@dataclass
class Books:
    """The Dataset indexed by ID, plus the resolved bank statement."""
    inv: pd.DataFrame
    ledger: pd.DataFrame
    bank: pd.DataFrame
    parties: pd.DataFrame
    lines: pd.DataFrame
    tax_rates: pd.DataFrame
    filings: pd.DataFrame
    as_of: pd.Timestamp


def py(value):
    """A plain Python value for JSON: dates as ISO text, missing as None."""
    if value is None or value is pd.NaT or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, pd.Period):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    return value


def period_of(date: pd.Timestamp) -> str:
    return date.strftime("%Y-%m")


def view(table: str, record_id: str, row: pd.Series, fields: list[str]) -> dict:
    return {"table": table, "id": record_id, "fields": {f: py(row[f]) for f in fields}}


def invoice_view(b: Books, invoice_id: str) -> dict:
    return view("invoices", invoice_id, b.inv.loc[invoice_id], INVOICE_FIELDS)


def ledger_view(b: Books, entry_id: str) -> dict:
    return view("ledger_entries", entry_id, b.ledger.loc[entry_id], LEDGER_FIELDS)


def bank_view(b: Books, txn_id: str) -> dict:
    return view("bank_transactions", txn_id, b.bank.loc[txn_id], BANK_FIELDS)


def line_view(b: Books, line_id: str) -> dict:
    return view("gstr2b_lines", line_id, b.lines.loc[line_id], LINE_FIELDS)


def diff(rows: list[tuple[str, object, object, object]]) -> list[dict]:
    """Field diffs from (field, left, right, expected). A cell differs when it is not equal to the value it is compared with."""
    out = []
    for field, left, right, expected in rows:
        left, right, expected = py(left), py(right), py(expected)
        other = expected if expected is not None else right
        out.append({"field": field, "label": FIELD_LABELS.get(field, field), "left": left, "right": right, "expected": expected,
                    "differs": other is not None and left != other})
    return out


def tax_split(invoice: pd.Series, impact_paise: int) -> dict[str, int]:
    """Spread an impact over tax types the way the invoice carries its tax."""
    if invoice["igst_paise"] != 0 or invoice["party_state_code"] != COMPANY_STATE and invoice["cgst_paise"] == 0:
        return {"igst": int(impact_paise), "cgst": 0, "sgst": 0}
    half = int(impact_paise) // 2
    return {"igst": 0, "cgst": int(impact_paise) - half, "sgst": half}


def finding(finding_type: str, period: str, entity_id: str, impact_type: str, impact_paise: int, title: str, reason: str,
            refs: list[tuple[str, str]], left: dict, right: dict | None = None, expected: dict | None = None,
            diffs: list[dict] | None = None, party_id: str | None = None, confidence: float = 1.0, deadline: str | None = None,
            split: dict[str, int] | None = None, invoice_id: str | None = None, impacts: dict[str, dict[str, int]] | None = None,
            what_to_do: str | None = None) -> dict:
    label, category, severity, rule_ref, rule_text, default_fix, _ = META[finding_type]
    # impacts maps each invoice (or the entity) to its share of the impact by tax type, so money is never counted twice.
    if impacts is None:
        impacts = {invoice_id or entity_id: split or {"other": int(impact_paise)}}
    return {
        "finding_type": finding_type, "label": label, "category": category, "severity": severity, "period": period,
        "entity_id": entity_id, "invoice_id": invoice_id, "impact_type": impact_type, "impact_paise": int(impact_paise),
        "confidence": float(confidence), "deadline": deadline, "party_id": party_id, "title": title, "reason": reason,
        "rule_ref": rule_ref, "rule_text": rule_text, "what_to_do": what_to_do or default_fix,
        "record_refs": [{"table": t, "id": i} for t, i in refs],
        "evidence": {"left": left, "right": right, "expected": expected, "impacts": impacts},
        "diff": diffs or [],
    }


def rupees(paise: int) -> str:
    """Rs with Indian grouping, no paise, for sentences."""
    whole = int(round(abs(int(paise)) / 100))
    digits = str(whole)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ("-" if paise < 0 else "") + "Rs " + ",".join(groups + [tail])


def nice_date(date) -> str:
    return pd.Timestamp(date).strftime("%d %b %Y").lstrip("0")
