"""Map the ML Dataset onto the store's Record tables (plan/03-data-model.md)."""
from __future__ import annotations

import pandas as pd

from .findings import Books, py
from .supplier_filing import line_period

PARTY_TYPE = {"VENDOR": "supplier", "CUSTOMER": "customer"}


def _int(value) -> int:
    """Empty money cells on payment and receipt rows are stored as zero."""
    return 0 if pd.isna(value) else int(value)


def build(dataset_id: str, b: Books, answer_key: pd.DataFrame) -> dict[str, list[dict]]:
    account_of = b.bank.dropna(subset=["resolved_party_id"]).groupby("resolved_party_id")["counterparty_account"].first().to_dict()
    true_net = dict(zip(answer_key["period"], answer_key["true_net_tax_liability_paise"]))
    return {
        "parties": [{
            "id": p.party_id, "dataset_id": dataset_id, "name": p.party_name, "party_type": PARTY_TYPE[p.party_type], "gstin": p.gstin,
            "pan": p.pan, "state_code": int(p.state_code), "gstin_status": p.gstin_status, "cancelled_from": py(p.cancelled_from),
            "bank_account": account_of.get(p.party_id),
        } for p in b.parties.itertuples()],
        "invoices": [{
            "id": i.invoice_id, "dataset_id": dataset_id, "kind": i.invoice_type.lower(), "doc_type": i.doc_type.lower(),
            "invoice_date": py(i.invoice_date), "period": i.invoice_date.strftime("%Y-%m"), "party_id": i.party_id, "party_gstin": i.party_gstin,
            "place_of_supply": int(i.place_of_supply), "hsn": int(i.hsn_sac), "category": i.category, "taxable_paise": int(i.taxable_value_paise),
            "rate_pct": int(i.tax_rate_pct), "cgst_paise": int(i.cgst_paise), "sgst_paise": int(i.sgst_paise), "igst_paise": int(i.igst_paise),
            "total_tax_paise": int(i.total_tax_paise), "total_paise": int(i.invoice_total_paise), "original_invoice_id": py(i.original_invoice_id),
        } for i in b.inv.itertuples()],
        "ledger_entries": [{
            "id": e.entry_id, "dataset_id": dataset_id, "posting_date": py(e.posting_date), "period": e.posting_date.strftime("%Y-%m"),
            "voucher_type": e.voucher_type.lower(), "account": e.ledger_account, "party_id": py(e.party_id), "invoice_ref": py(e.invoice_ref),
            "taxable_paise": _int(e.taxable_amount_paise), "total_tax_paise": _int(e.total_tax_paise), "total_paise": int(e.total_amount_paise),
            "debit_paise": int(e.debit_paise), "credit_paise": int(e.credit_paise), "utr_ref": py(e.utr_ref), "narration": e.narration,
        } for e in b.ledger.itertuples()],
        "bank_transactions": [{
            "id": t.txn_id, "dataset_id": dataset_id, "txn_date": py(t.txn_date), "period": t.txn_date.strftime("%Y-%m"),
            "direction": t.direction.lower(), "amount_paise": int(t.amount_paise), "counterparty_name": t.counterparty_name,
            "counterparty_account": t.counterparty_account, "resolved_party_id": py(t.resolved_party_id), "payment_mode": t.payment_mode,
            "utr": t.utr, "narration": t.narration,
        } for t in b.bank.itertuples()],
        "gstr2b_lines": [{
            "id": l.line_id, "dataset_id": dataset_id, "supplier_gstin": l.gstin_supplier, "trade_name": l.trade_name,
            "invoice_number": l.invoice_number, "invoice_date": py(l.invoice_date), "invoice_value_paise": int(l.invoice_value_paise),
            "place_of_supply": int(l.place_of_supply), "rate_pct": int(l.rate), "taxable_paise": int(l.taxable_value_paise),
            "igst_paise": int(l.igst_paise), "cgst_paise": int(l.cgst_paise), "sgst_paise": int(l.sgst_paise),
            "return_period": line_period(l.return_period), "itc_available": int(l.itc_availability == "Y"),
        } for l in b.lines.itertuples()],
        "tax_rates": [{
            "dataset_id": dataset_id, "hsn": int(r.hsn_sac), "category": r.category, "rate_pct": int(r.gst_rate_pct),
            "effective_from": py(r.effective_from), "effective_to": py(r.effective_to), "is_exempt": int(r.is_exempt),
        } for r in b.tax_rates.itertuples()],
        "filings": [{
            "dataset_id": dataset_id, "period": f.period, "due_date": py(f.due_date), "filing_date": py(f.filing_date),
            "output_tax_paise": int(f.total_output_tax_paise), "itc_claimed_paise": int(f.total_itc_claimed_paise),
            "net_payable_paise": int(f.net_tax_payable_paise), "true_net_paise": int(true_net[f.period]),
        } for f in b.filings.itertuples()],
    }
