"""Purchase invoices against GSTR-2B lines, by rule score. The Supplier GSTIN must be equal; it is never fuzzy-matched."""
from __future__ import annotations

import pandas as pd
from ledgerlens_ml import id_serial, normalise_invoice_id

from .findings import Books, diff, finding, invoice_view, line_view, period_of, rupees, tax_split
from .matching import match_row

VALUE_TOLERANCE = 0.01


def line_period(return_period: str) -> str:
    """MMYYYY as written in GSTR-2B to YYYY-MM."""
    return f"{return_period[2:]}-{return_period[:2]}"


def _line_tax(line: pd.Series) -> int:
    return int(line["igst_paise"] + line["cgst_paise"] + line["sgst_paise"])


def check(b: Books, duplicate_invoices: set[str]) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    matches: list[dict] = []
    gstin_of = b.parties["gstin"].to_dict()
    party_of_gstin = {g: p for p, g in gstin_of.items()}
    lines_by_key: dict[tuple[str, str], list[str]] = {}
    for line_id, line in b.lines.iterrows():
        lines_by_key.setdefault((line["gstin_supplier"], id_serial(line["invoice_number"])), []).append(line_id)
    used: set[str] = set()

    purchases = b.inv[(b.inv["invoice_type"] == "PURCHASE") & (b.inv["doc_type"] == "INVOICE")]
    for invoice_id, inv in purchases.iterrows():
        month = inv["invoice_date"].to_period("M")
        period = str(month)
        allowed = {str(month), str(month + 1)}
        options = [l for l in lines_by_key.get((gstin_of[inv["party_id"]], id_serial(invoice_id)), [])
                   if l not in used and line_period(b.lines.loc[l, "return_period"]) in allowed]
        tax = int(inv["total_tax_paise"])
        if not options:
            matches.append(match_row("supplier_filing", period, [invoice_id], [], "exact", 0.0, "unmatched", ["No GSTR-2B line from this Supplier carries this invoice number"]))
            if invoice_id not in duplicate_invoices:
                findings.append(finding("MISSING_IN_2B", period=period, entity_id=invoice_id, impact_type="itc_at_risk", impact_paise=tax,
                                        title=f"{rupees(tax)} ITC at risk: {inv['party_name']} has not reported {invoice_id}",
                                        reason=f"GSTR-2B for {month.strftime('%b %Y')} and the month after has no line from GSTIN {gstin_of[inv['party_id']]} with this invoice number.",
                                        refs=[("invoices", invoice_id)], left=invoice_view(b, invoice_id), party_id=inv["party_id"], invoice_id=invoice_id,
                                        split=tax_split(inv, tax), confidence=0.95))
            continue
        line_id = options[0]
        used.add(line_id)
        line = b.lines.loc[line_id]
        same_number = normalise_invoice_id(line["invoice_number"]) == normalise_invoice_id(invoice_id)
        confidence = 1.0 if line["invoice_number"] == invoice_id else 0.97 if same_number else 0.9
        how = "Invoice number matches exactly" if line["invoice_number"] == invoice_id else f"Supplier wrote the number as {line['invoice_number']}; the serial matches"
        matches.append(match_row("supplier_filing", period, [invoice_id], [line_id], "exact" if line["invoice_number"] == invoice_id else "normalised",
                                 confidence, "auto", [how, "Supplier GSTIN is equal", f"Reported in return period {line_period(line['return_period'])}"]))
        common = dict(period=period, entity_id=invoice_id, refs=[("invoices", invoice_id), ("gstr2b_lines", line_id)], left=invoice_view(b, invoice_id),
                      right=line_view(b, line_id), party_id=inv["party_id"], invoice_id=invoice_id, confidence=confidence)
        taxable, reported = int(inv["taxable_value_paise"]), int(line["taxable_value_paise"])
        if abs(taxable - reported) > max(VALUE_TOLERANCE * taxable, 100):
            gap = abs(tax - _line_tax(line))
            less = _line_tax(line) < tax
            findings.append(finding("GSTR2B_VALUE_MISMATCH", impact_type="itc_at_risk" if less else "itc_found", impact_paise=gap,
                                    title=f"{inv['party_name']} reported {rupees(reported)} for {invoice_id}, the books show {rupees(taxable)}",
                                    reason=f"The Supplier's GSTR-2B line carries {rupees(_line_tax(line))} of tax and the invoice {rupees(tax)}. " +
                                           ("Only the lower amount is safe to claim." if less else "The Supplier reported more credit than was booked."),
                                    diffs=diff([("taxable_value_paise", taxable, reported, None), ("total_tax_paise", tax, _line_tax(line), None)]),
                                    split=tax_split(inv, gap), **common))
        if line_period(line["return_period"]) != period:
            findings.append(finding("PERIOD_SHIFT", impact_type="none", impact_paise=tax,
                                    title=f"{invoice_id} shows in GSTR-2B for {line_period(line['return_period'])}, not {period}",
                                    reason=f"The Supplier reported this invoice one Return period late, so its {rupees(tax)} of credit can be claimed only in that month.",
                                    diffs=diff([("invoice_date", period, line_period(line["return_period"]), None)]), **common))

    for line_id, line in b.lines[~b.lines.index.isin(used)].iterrows():
        tax = _line_tax(line)
        findings.append(finding("MISSING_IN_BOOKS", period=line_period(line["return_period"]), entity_id=line_id, impact_type="itc_found", impact_paise=tax,
                                title=f"{rupees(tax)} ITC found: {line['trade_name']} reported {line['invoice_number']}, not in your books",
                                reason="GSTR-2B shows this purchase against your GSTIN, but no invoice with this number from this Supplier is booked.",
                                refs=[("gstr2b_lines", line_id)], left=line_view(b, line_id), party_id=party_of_gstin.get(line["gstin_supplier"]),
                                split={"igst": int(line["igst_paise"]), "cgst": int(line["cgst_paise"]), "sgst": int(line["sgst_paise"])}, confidence=0.9))
    return findings, matches
