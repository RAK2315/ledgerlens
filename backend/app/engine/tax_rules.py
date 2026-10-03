"""Tax checks on each invoice: Effective rate, tax type, arithmetic, exempt, zero tax, GSTIN validity."""
from __future__ import annotations

import pandas as pd
from ledgerlens_ml import is_valid_gstin

from .findings import COMPANY_STATE, Books, diff, finding, invoice_view, nice_date, period_of, rupees, tax_split

# Rounding differences under one rupee are normal and never reported.
TOLERANCE_PAISE = 100


def effective_rate(tax_rates: pd.DataFrame, hsn: int, date: pd.Timestamp) -> dict | None:
    """The rate table row in force for an HSN code on a date."""
    rows = tax_rates[(tax_rates["hsn_sac"] == hsn) & (tax_rates["effective_from"] <= date)
                     & (tax_rates["effective_to"].isna() | (tax_rates["effective_to"] >= date))]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {"rate": int(row["gst_rate_pct"]), "is_exempt": bool(row["is_exempt"]), "effective_from": row["effective_from"], "category": row["category"]}


def expected_tax(taxable_paise: int, rate_pct: int) -> int:
    return int((taxable_paise * rate_pct + 50) // 100)


def _direction(kind: str, charged: int, expected: int) -> str:
    """Too much tax on a sale is excess tax; on a purchase the extra credit is at risk. Too little on a sale is short tax."""
    if kind == "SALES":
        return "excess_tax" if charged > expected else "short_tax"
    return "itc_at_risk" if charged > expected else "none"


FIXES = {
    "excess_tax": "Issue a credit note to the Customer for the excess tax and correct the invoice.",
    "short_tax": "Raise a debit note to the Customer for the tax not charged and correct the invoice.",
    "itc_at_risk": "Ask the Supplier for a credit note for the excess tax. Claim credit only on the correct amount until it arrives.",
    "none": "Ask the Supplier for a corrected invoice.",
}


def check(b: Books) -> list[dict]:
    out: list[dict] = []
    master_gstin = b.parties["gstin"].to_dict()
    for invoice_id, inv in b.inv[b.inv["doc_type"] == "INVOICE"].iterrows():
        kind, period = inv["invoice_type"], period_of(inv["invoice_date"])
        tax, taxable, rate = int(inv["total_tax_paise"]), int(inv["taxable_value_paise"]), int(inv["tax_rate_pct"])
        left = invoice_view(b, invoice_id)
        common = dict(period=period, entity_id=invoice_id, refs=[("invoices", invoice_id)], left=left, party_id=inv["party_id"], invoice_id=invoice_id)

        good = master_gstin.get(inv["party_id"])
        if not is_valid_gstin(inv["party_gstin"]) or inv["party_gstin"] != good:
            why = ("it has the wrong length" if len(str(inv["party_gstin"])) != 15 else
                   "its check character is wrong" if not is_valid_gstin(inv["party_gstin"]) else "it is not this Party's registered GSTIN")
            out.append(finding("INVALID_GSTIN", impact_type="itc_at_risk" if kind == "PURCHASE" else "none",
                               impact_paise=tax if kind == "PURCHASE" else 0,
                               title=f"GSTIN {inv['party_gstin']} on {invoice_id} is not valid",
                               reason=f"The GSTIN on the invoice is {inv['party_gstin']}: {why}. The party master has {good}.",
                               expected={"party_gstin": good}, diffs=diff([("party_gstin", inv["party_gstin"], None, good)]),
                               split=tax_split(inv, tax), **common))

        rule = effective_rate(b.tax_rates, int(inv["hsn_sac"]), inv["invoice_date"])
        if rule is not None:
            want = expected_tax(taxable, rule["rate"])
            expected = {"tax_rate_pct": rule["rate"], "total_tax_paise": want, "effective_from": rule["effective_from"].strftime("%Y-%m-%d")}
            rows = diff([("tax_rate_pct", rate, None, rule["rate"]), ("total_tax_paise", tax, None, want)])
            item = f"HSN {inv['hsn_sac']} ({inv['category']})"
            if rule["is_exempt"] and tax > TOLERANCE_PAISE:
                out.append(finding("EXEMPT_ITEM_TAXED", impact_type="excess_tax" if kind == "SALES" else "itc_at_risk", impact_paise=tax,
                                   title=f"{rupees(tax)} of tax charged on an exempt item, {invoice_id}",
                                   reason=f"{item} is exempt in the rate table, but the invoice charges {rate} percent.",
                                   expected=expected, diffs=rows, split=tax_split(inv, tax), **common))
            elif rule["rate"] > 0 and rate == 0 and tax == 0:
                out.append(finding("TAXABLE_ITEM_ZERO_TAX", impact_type="short_tax" if kind == "SALES" else "none", impact_paise=want,
                                   what_to_do=FIXES["short_tax" if kind == "SALES" else "none"],
                                   title=f"No tax charged on a taxable item, {invoice_id}: {rupees(want)} missing",
                                   reason=f"{item} carries {rule['rate']} percent in the rate table, but the invoice charges no tax.",
                                   expected=expected, diffs=rows, split=tax_split(inv, want), **common))
            elif rate != rule["rate"]:
                gap = abs(tax - want)
                changed = rule["effective_from"] > b.tax_rates["effective_from"].min()
                since = f" The rate changed on {nice_date(rule['effective_from'])}." if changed else ""
                stale = f" since {nice_date(rule['effective_from'])}" if changed else ""
                word = {"excess_tax": "excess tax", "short_tax": "short tax", "itc_at_risk": "ITC at risk", "none": "tax difference"}[_direction(kind, tax, want)]
                out.append(finding("WRONG_TAX_RATE", impact_type=_direction(kind, tax, want), impact_paise=gap,
                                   what_to_do=FIXES[_direction(kind, tax, want)],
                                   title=f"{rupees(gap)} {word} on {invoice_id}: charged {rate} percent, the rate is {rule['rate']} percent{stale}",
                                   reason=f"{item} was taxed at {rate} percent. The rate in force on {nice_date(inv['invoice_date'])} is {rule['rate']} percent.{since}",
                                   expected=expected, diffs=rows, split=tax_split(inv, gap), **common))
            elif abs(tax - expected_tax(taxable, rate)) > TOLERANCE_PAISE:
                gap = abs(tax - want)
                out.append(finding("TAX_CALC_ERROR", impact_type=_direction(kind, tax, want), impact_paise=gap,
                                   what_to_do=FIXES[_direction(kind, tax, want)],
                                   title=f"Tax on {invoice_id} is off by {rupees(gap)}",
                                   reason=f"{rupees(taxable)} at {rate} percent is {rupees(want)}, but the invoice shows {rupees(tax)}.",
                                   expected=expected, diffs=rows, split=tax_split(inv, gap), **common))

        interstate = int(inv["party_state_code"]) != COMPANY_STATE
        has_igst = inv["igst_paise"] != 0
        if tax > 0 and interstate != has_igst:
            right_type = "IGST" if interstate else "CGST plus SGST"
            wrong_type = "CGST plus SGST" if interstate else "IGST"
            where = "another state" if interstate else "the same state"
            out.append(finding("WRONG_TAX_TYPE", impact_type="itc_at_risk" if kind == "PURCHASE" else "short_tax", impact_paise=tax,
                               title=f"{invoice_id} charges {wrong_type} where {right_type} applies",
                               reason=f"The Party is in {where} (state code {int(inv['party_state_code'])}), so the supply carries {right_type}. The invoice charges {wrong_type}.",
                               expected={"tax_type": right_type},
                               diffs=diff([("igst_paise", inv["igst_paise"], None, tax if interstate else 0),
                                           ("cgst_paise", inv["cgst_paise"], None, 0 if interstate else tax - tax // 2),
                                           ("sgst_paise", inv["sgst_paise"], None, 0 if interstate else tax // 2)]),
                               split=tax_split(inv, tax), **common))
    return out
