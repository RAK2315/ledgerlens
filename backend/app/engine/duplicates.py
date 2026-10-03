"""Duplicate invoices: same Party, same value and tax, close dates, a new invoice number."""
from __future__ import annotations

from .findings import Books, diff, finding, invoice_view, nice_date, period_of, rupees, tax_split

MAX_DAYS_APART = 45


def _serial(invoice_id: str) -> int:
    digits = "".join(ch for ch in invoice_id.split("-")[-1] if ch.isdigit())
    return int(digits or 0)


def check(b: Books) -> list[dict]:
    out: list[dict] = []
    real = b.inv[(b.inv["doc_type"] == "INVOICE") & (b.inv["total_tax_paise"] >= 0)]
    for _, group in real.groupby(["party_id", "invoice_type", "taxable_value_paise", "total_tax_paise"]):
        if len(group) < 2:
            continue
        ordered = sorted(group.index, key=_serial)
        original = b.inv.loc[ordered[0]]
        for invoice_id in ordered[1:]:
            inv = b.inv.loc[invoice_id]
            if abs((inv["invoice_date"] - original["invoice_date"]).days) > MAX_DAYS_APART:
                continue
            tax = int(inv["total_tax_paise"])
            purchase = inv["invoice_type"] == "PURCHASE"
            out.append(finding(
                "DUPLICATE_INVOICE", period=period_of(inv["invoice_date"]), entity_id=invoice_id,
                impact_type="itc_at_risk" if purchase else "excess_tax", impact_paise=tax,
                title=f"{invoice_id} repeats {ordered[0]}: {rupees(tax)} of tax counted twice",
                reason=f"Same Party, same taxable value ({rupees(inv['taxable_value_paise'])}) and tax as {ordered[0]} dated {nice_date(original['invoice_date'])}, under a new invoice number.",
                refs=[("invoices", invoice_id), ("invoices", ordered[0])], left=invoice_view(b, invoice_id), right=invoice_view(b, ordered[0]),
                diffs=diff([("invoice_date", inv["invoice_date"], original["invoice_date"], None),
                            ("taxable_value_paise", inv["taxable_value_paise"], original["taxable_value_paise"], None),
                            ("total_tax_paise", inv["total_tax_paise"], original["total_tax_paise"], None)]),
                party_id=inv["party_id"], split=tax_split(inv, tax), invoice_id=invoice_id, confidence=0.95))
    return out
