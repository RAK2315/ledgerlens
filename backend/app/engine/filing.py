"""The filed return against the books: late filing, under-reported output tax, over-claimed credit, short tax payment."""
from __future__ import annotations

from .findings import Books, bank_view, finding, nice_date, py, rupees

# Smaller gaps come from single invoice errors, which have their own Findings.
GAP_TOLERANCE_PAISE = 1_00_000 * 100


def filing_view(row) -> dict:
    fields = ["due_date", "filing_date", "total_output_tax_paise", "total_itc_claimed_paise", "net_tax_payable_paise"]
    return {"table": "filings", "id": row["period"], "fields": {f: py(row[f]) for f in fields}}


def check(b: Books) -> list[dict]:
    out: list[dict] = []
    month = b.inv["invoice_date"].dt.strftime("%Y-%m")
    for _, filed in b.filings.iterrows():
        period = filed["period"]
        common = dict(period=period, entity_id=period, refs=[("filings", period)], left=filing_view(filed))
        if filed["filing_date"] > filed["due_date"]:
            days = (filed["filing_date"] - filed["due_date"]).days
            out.append(finding("LATE_FILING", impact_type="none", impact_paise=0, deadline=filed["due_date"].strftime("%Y-%m-%d"),
                               title=f"The return for {period} was filed {days} days late",
                               reason=f"It was due on {nice_date(filed['due_date'])} and filed on {nice_date(filed['filing_date'])}.", **common))
        sales_tax = int(b.inv.loc[(month == period) & (b.inv["invoice_type"] == "SALES"), "total_tax_paise"].sum())
        purchase_tax = int(b.inv.loc[(month == period) & (b.inv["invoice_type"] == "PURCHASE"), "total_tax_paise"].sum())
        declared_output, declared_itc = int(filed["total_output_tax_paise"]), int(filed["total_itc_claimed_paise"])
        if sales_tax - declared_output > GAP_TOLERANCE_PAISE:
            out.append(finding("UNDER_REPORTED_OUTPUT_TAX", impact_type="short_tax", impact_paise=sales_tax - declared_output,
                               title=f"The return for {period} declares {rupees(sales_tax - declared_output)} less output tax than the sales invoices",
                               reason=f"Sales invoices carry {rupees(sales_tax)} of tax; the return declares {rupees(declared_output)}.",
                               expected={"total_output_tax_paise": sales_tax}, **common))
        if declared_itc - purchase_tax > GAP_TOLERANCE_PAISE:
            out.append(finding("ITC_OVERCLAIM", impact_type="itc_at_risk", impact_paise=declared_itc - purchase_tax,
                               title=f"The return for {period} claims {rupees(declared_itc - purchase_tax)} more credit than the purchase invoices",
                               reason=f"Purchase invoices carry {rupees(purchase_tax)} of tax; the return claims {rupees(declared_itc)}.",
                               expected={"total_itc_claimed_paise": purchase_tax}, **common))
        challans = b.bank[b.bank["narration"].str.contains(f"GST PMT {period}", regex=False)]
        if not challans.empty:
            paid = int(challans["amount_paise"].sum())
            short = int(filed["net_tax_payable_paise"]) - paid
            if short > GAP_TOLERANCE_PAISE:
                txn_id = challans.index[0]
                out.append(finding("TAX_SHORT_PAYMENT", period=period, entity_id=txn_id, impact_type="short_tax", impact_paise=short,
                                   title=f"Tax paid for {period} is {rupees(short)} less than the return declares",
                                   reason=f"The return declares {rupees(filed['net_tax_payable_paise'])} payable; the bank shows {rupees(paid)} paid.",
                                   refs=[("bank_transactions", txn_id), ("filings", period)], left=bank_view(b, txn_id), right=filing_view(filed)))
    return out
