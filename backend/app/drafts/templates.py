"""One template per Draft kind. Used when there is no model output, and as the facts the model must keep."""
from __future__ import annotations

from ..engine.findings import nice_date, rupees
from ..engine.labels import META
from ..engine.run import COMPANY

SIGN_OFF = f"Accounts team\n{COMPANY['name']}\nGSTIN {COMPANY['gstin']}"


def draft_kind(finding: dict) -> str:
    kind = META[finding["finding_type"]][6]
    left = finding["evidence"]["left"]
    purchase = left["table"] == "invoices" and left["fields"].get("invoice_type") == "PURCHASE"
    return "credit_note_request" if kind == "customer_credit_note" and purchase else kind


def facts(finding: dict, party_name: str | None) -> dict:
    """The facts a Draft may use. Nothing outside this goes into the text."""
    left = finding["evidence"]["left"]
    fields = left["fields"]
    return {
        "finding": finding["title"], "why": finding["reason"], "next_step": finding["what_to_do"],
        "amount": rupees(finding["impact_paise"]), "record": left["id"], "party": party_name or fields.get("party_name") or fields.get("trade_name") or "the Party",
        "invoice_date": nice_date(fields["invoice_date"]) if fields.get("invoice_date") else None, "invoice_total": rupees(fields["invoice_total_paise"]) if fields.get("invoice_total_paise") is not None else None,
        "company": COMPANY["name"], "company_gstin": COMPANY["gstin"],
        # Tax charged too low is corrected with a debit note, too high with a credit note.
        "document": "debit note" if finding["impact_type"] == "short_tax" else "credit note",
    }


def build(finding: dict, party_name: str | None) -> dict:
    kind, f = draft_kind(finding), facts(finding, party_name)
    record = f["record"]
    if kind == "supplier_email":
        subject = f"{record}: please correct your GST filing"
        body = (f"Dear {f['party']} team,\n\nWe are reconciling our purchases with GSTR-2B and found a problem with invoice {record}"
                f"{' dated ' + f['invoice_date'] if f['invoice_date'] else ''}.\n\n{f['why']}\n\n"
                f"{f['amount']} of input tax credit depends on this. Please look into it and confirm once it is corrected in your return.\n\nRegards,\n{SIGN_OFF}")
        recipient = f"{f['party']} (accounts)"
    elif kind == "customer_credit_note":
        note = f["document"]
        subject = f"{note.capitalize()} for {record}: {f['amount']}"
        body = (f"Dear {f['party']} team,\n\nWe reviewed invoice {record}{' dated ' + f['invoice_date'] if f['invoice_date'] else ''} and found an error on our side.\n\n"
                f"{f['why']}\n\nWe are issuing a {note} for {f['amount']} and will send the corrected invoice. Please adjust your records.\n\nRegards,\n{SIGN_OFF}")
        recipient = f"{f['party']} (accounts)"
    elif kind == "credit_note_request":
        subject = f"Request for credit note: {record}, {f['amount']}"
        body = (f"Dear {f['party']} team,\n\nWe found a problem with your invoice {record}{' dated ' + f['invoice_date'] if f['invoice_date'] else ''}.\n\n"
                f"{f['why']}\n\nPlease issue a credit note for {f['amount']} or a corrected invoice, so that we can claim the right credit.\n\nRegards,\n{SIGN_OFF}")
        recipient = f"{f['party']} (accounts)"
    else:
        subject = f"Correction for {record}"
        body = (f"Correction note for the books of {COMPANY['name']}\n\nRecord: {record}\nFinding: {f['finding']}\n\nWhy: {f['why']}\n\n"
                f"Entry to make: {f['next_step']}\nAmount involved: {f['amount']}\n\nPrepared for approval by the accounts lead.")
        recipient = "Accounts lead (internal)"
    return {"kind": kind, "recipient": recipient, "subject": subject, "body": body}
