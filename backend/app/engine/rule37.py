"""Purchases unpaid for over 180 days, and purchases from Suppliers whose GSTIN is cancelled."""
from __future__ import annotations

import pandas as pd

from .findings import Books, finding, invoice_view, nice_date, period_of, rupees, tax_split

UNPAID_DAYS = 180


def check(b: Books, paid: dict[str, list[str]], skip: set[str]) -> list[dict]:
    """skip holds invoices already reported as duplicates or as paid in the books but not in the bank."""
    out: list[dict] = []
    purchases = b.inv[(b.inv["invoice_type"] == "PURCHASE") & (b.inv["doc_type"] == "INVOICE")]
    for invoice_id, inv in purchases.iterrows():
        tax = int(inv["total_tax_paise"])
        common = dict(period=period_of(inv["invoice_date"]), entity_id=invoice_id, impact_type="itc_at_risk", impact_paise=tax, refs=[("invoices", invoice_id)],
                      left=invoice_view(b, invoice_id), party_id=inv["party_id"], invoice_id=invoice_id, split=tax_split(inv, tax))
        days_open = (b.as_of - inv["invoice_date"]).days
        if invoice_id not in paid and invoice_id not in skip and days_open > UNPAID_DAYS:
            deadline = inv["invoice_date"] + pd.Timedelta(days=UNPAID_DAYS)
            out.append(finding("RULE_37_UNPAID_180", deadline=deadline.strftime("%Y-%m-%d"),
                               title=f"{rupees(tax)} ITC at risk: {invoice_id} unpaid for {days_open} days",
                               reason=f"No bank payment to {inv['party_name']} settles this invoice. The 180 days ran out on {nice_date(deadline)}.",
                               confidence=0.9, **common))
        party = b.parties.loc[inv["party_id"]]
        if party["gstin_status"] == "cancelled" and inv["invoice_date"] >= party["cancelled_from"]:
            out.append(finding("CANCELLED_GSTIN",
                               title=f"{rupees(tax)} ITC at risk: {inv['party_name']}'s GSTIN was cancelled before {invoice_id}",
                               reason=f"GSTIN {party['gstin']} is cancelled from {nice_date(party['cancelled_from'])}. This invoice is dated {nice_date(inv['invoice_date'])}.",
                               **common))
    return out
