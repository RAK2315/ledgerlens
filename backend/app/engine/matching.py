"""Turn matcher results into Matches and the Findings that follow from them (booking and payment sides)."""
from __future__ import annotations

import pandas as pd
from ledgerlens_ml import id_serial, narration_id_tokens, normalise_invoice_id
from rapidfuzz.distance import DamerauLevenshtein

from .findings import Books, bank_view, diff, finding, invoice_view, ledger_view, nice_date, period_of, rupees, tax_split
from .one_to_many import TOLERANCE_PAISE, find_subset

CIRCULAR_ROUND_PAISE = 50_000 * 100
CIRCULAR_MAX_DAYS = 10
BOOKING_VOUCHERS = ("SALES", "PURCHASE", "CREDIT_NOTE")
SIMILAR_ID = 0.75


def _layer(result) -> str:
    f = result.features
    if not f:
        return "model"
    if f.get("id_exact"):
        return "exact"
    if f.get("id_norm_exact"):
        return "normalised"
    if f.get("id_serial_equal") or (f.get("id_dl_sim") or 0) >= 0.85:
        return "fuzzy"
    return "model"


def match_row(kind: str, period: str, invoice_ids: list[str], right_ids: list[str], layer: str, confidence: float, band: str, reasons: list[str]) -> dict:
    return {"kind": kind, "period": period, "invoice_id": invoice_ids[0], "invoice_ids": invoice_ids, "right_ids": right_ids,
            "layer": layer, "confidence": float(confidence), "band": band, "reasons": reasons}


def _booked_pair(b: Books, invoice_id: str, entry_id: str, confidence: float) -> list[dict]:
    """Findings on an invoice and the ledger entry that books it."""
    inv, entry = b.inv.loc[invoice_id], b.ledger.loc[entry_id]
    period = period_of(inv["invoice_date"])
    common = dict(period=period, entity_id=entry_id, party_id=inv["party_id"], invoice_id=invoice_id, confidence=max(confidence, 0.5),
                  left=invoice_view(b, invoice_id), right=ledger_view(b, entry_id), refs=[("invoices", invoice_id), ("ledger_entries", entry_id)])
    out = []
    gap = abs(abs(int(entry["total_amount_paise"])) - abs(int(inv["invoice_total_paise"])))
    if gap > TOLERANCE_PAISE:
        out.append(finding("AMOUNT_MISMATCH", impact_type="none", impact_paise=gap,
                           title=f"{invoice_id} is booked {rupees(gap)} away from the invoice total",
                           reason=f"The invoice total is {rupees(abs(inv['invoice_total_paise']))} but the ledger entry shows {rupees(entry['total_amount_paise'])}.",
                           diffs=diff([("invoice_total_paise", abs(int(inv["invoice_total_paise"])), abs(int(entry["total_amount_paise"])), None)]), **common))
    if period_of(entry["posting_date"]) != period:
        out.append(finding("DATE_MISMATCH", impact_type="none", impact_paise=abs(int(inv["total_tax_paise"])),
                           title=f"{invoice_id} is booked in {entry['posting_date']:%b %Y}, not in {inv['invoice_date']:%b %Y}",
                           reason=f"The invoice is dated {nice_date(inv['invoice_date'])} but was posted on {nice_date(entry['posting_date'])}, so its tax lands in another Return period.",
                           diffs=diff([("invoice_date", inv["invoice_date"], entry["posting_date"], None)]), **common))
    if entry["invoice_ref"] != invoice_id:
        out.append(finding("INVOICE_ID_MISMATCH", impact_type="none", impact_paise=0,
                           title=f"Ledger says {entry['invoice_ref']}, the invoice is {invoice_id}",
                           reason=f"The ledger reference {entry['invoice_ref']} is not this invoice's number. Amount and Party match {invoice_id}.",
                           diffs=diff([("invoice_ref", invoice_id, entry["invoice_ref"], None)]), **common))
    return out


def booking(b: Books, results: list) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    matches: list[dict] = []
    used: dict[str, str] = {r.right_id: r.invoice_id for r in results if r.right_id}
    spare = b.ledger[b.ledger["voucher_type"].isin(BOOKING_VOUCHERS) & ~b.ledger.index.isin(used)]
    for r in results:
        inv = b.inv.loc[r.invoice_id]
        period = period_of(inv["invoice_date"])
        if r.right_id:
            matches.append(match_row("booking", period, [r.invoice_id], [r.right_id], _layer(r), r.confidence, r.band, r.reasons))
            findings += _booked_pair(b, r.invoice_id, r.right_id, r.confidence)
            continue
        # A typo in the reference or a far-off posting date can hide a booking from the matcher; Party and amount still give it away.
        voucher = inv["invoice_type"] if inv["doc_type"] == "INVOICE" else "CREDIT_NOTE"
        gap = (spare["total_amount_paise"].abs() - abs(int(inv["invoice_total_paise"]))).abs()
        twins = spare[(spare["party_id"] == inv["party_id"]) & (spare["voucher_type"] == voucher) & (gap <= TOLERANCE_PAISE) & ~spare.index.isin(used)]
        if not twins.empty:
            entry_id = twins.index[0]
            used[entry_id] = r.invoice_id
            matches.append(match_row("booking", period, [r.invoice_id], [entry_id], "fuzzy", 0.8, "review",
                                     ["Same Party and the same amount to the rupee", f"Ledger reference reads {twins.iloc[0]['invoice_ref']}"]))
            findings += _booked_pair(b, r.invoice_id, entry_id, 0.8)
            continue
        matches.append(match_row("booking", period, [r.invoice_id], [], "model", r.confidence, "unmatched", r.reasons))
        tax = abs(int(inv["total_tax_paise"]))
        findings.append(finding("MISSING_LEDGER_ENTRY", period=period, entity_id=r.invoice_id, impact_type="itc_at_risk" if inv["invoice_type"] == "PURCHASE" else "short_tax",
                                impact_paise=tax, title=f"{r.invoice_id} was never booked: {rupees(tax)} of tax missing from the books",
                                reason="No ledger entry for this Party carries this invoice number or its amount.",
                                refs=[("invoices", r.invoice_id)], left=invoice_view(b, r.invoice_id), split=tax_split(inv, tax),
                                party_id=inv["party_id"], invoice_id=r.invoice_id, confidence=0.9))

    by_norm = {(inv["party_id"], normalise_invoice_id(invoice_id)): invoice_id for invoice_id, inv in b.inv.iterrows()}
    entry_of = {invoice_id: entry_id for entry_id, invoice_id in used.items()}
    for entry_id, entry in spare[~spare.index.isin(used)].iterrows():
        period = period_of(entry["posting_date"])
        invoice_id = by_norm.get((entry["party_id"], normalise_invoice_id(entry["invoice_ref"])))
        if invoice_id and invoice_id in entry_of:
            first = entry_of[invoice_id]
            tax = abs(int(entry["total_tax_paise"])) if pd.notna(entry["total_tax_paise"]) else 0
            findings.append(finding("DUPLICATE_LEDGER_ENTRY", period=period, entity_id=entry_id, impact_type="itc_at_risk" if entry["voucher_type"] == "PURCHASE" else "excess_tax",
                                    impact_paise=tax, title=f"{invoice_id} is booked twice: {rupees(tax)} of tax counted twice",
                                    reason=f"Ledger entries {first} and {entry_id} both record invoice {invoice_id}.",
                                    refs=[("ledger_entries", entry_id), ("ledger_entries", first), ("invoices", invoice_id)],
                                    left=ledger_view(b, entry_id), right=ledger_view(b, first), party_id=entry["party_id"], invoice_id=invoice_id,
                                    split=tax_split(b.inv.loc[invoice_id], tax)))
        else:
            findings.append(finding("ORPHAN_LEDGER_ENTRY", period=period, entity_id=entry_id, impact_type="none", impact_paise=abs(int(entry["total_amount_paise"])),
                                    title=f"Booking {entry_id} refers to {entry['invoice_ref']}, which does not exist",
                                    reason=f"No invoice numbered {entry['invoice_ref']} with this amount is in the invoice register for this Party.",
                                    refs=[("ledger_entries", entry_id)], left=ledger_view(b, entry_id), party_id=entry["party_id"]))
    return findings, matches


def _quotes(narration: str, invoice_id: str) -> bool:
    tokens = narration_id_tokens(narration)
    return any(normalise_invoice_id(t) == normalise_invoice_id(invoice_id) or id_serial(t) == id_serial(invoice_id) for t in tokens)


def _money_entries(b: Books) -> pd.DataFrame:
    """Payment and receipt ledger entries with the invoice each one settles, allowing for a mistyped reference."""
    entries = b.ledger[b.ledger["voucher_type"].isin(["PAYMENT", "RECEIPT"]) & b.ledger["invoice_ref"].notna()].copy()
    by_party: dict[str, list[tuple[str, int]]] = {}
    for invoice_id, inv in b.inv[b.inv["doc_type"] == "INVOICE"].iterrows():
        by_party.setdefault(inv["party_id"], []).append((invoice_id, int(inv["invoice_total_paise"])))
    targets = []
    for entry in entries.itertuples():
        amount, ref = abs(int(entry.total_amount_paise)), entry.invoice_ref
        named = ref if ref in b.inv.index and b.inv.loc[ref, "party_id"] == entry.party_id else None
        target = named
        if named is None or abs(int(b.inv.loc[named, "invoice_total_paise"]) - amount) > TOLERANCE_PAISE:
            alike = [(DamerauLevenshtein.normalized_similarity(ref.upper(), i), i) for i, total in by_party.get(entry.party_id, [])
                     if i != named and abs(total - amount) <= TOLERANCE_PAISE]
            alike = [pair for pair in alike if pair[0] >= SIMILAR_ID or normalise_invoice_id(ref) == normalise_invoice_id(pair[1])]
            if alike:
                target = max(alike)[1]
        targets.append(target)
    entries["target"] = targets
    entries["amount"] = entries["total_amount_paise"].abs().astype(int)
    return entries


def payments(b: Books, results: list) -> tuple[list[dict], list[dict], dict[str, list[str]]]:
    """Findings, Matches and, for every paid invoice, the bank transactions that paid it."""
    findings: list[dict] = []
    by_invoice = {r.invoice_id: r for r in results}
    assigned = {r.invoice_id: r.right_id for r in results if r.right_id}
    used = set(assigned.values())
    paid: dict[str, list[str]] = {i: [t] for i, t in assigned.items()}
    groups: list[tuple[list[str], list[str]]] = []
    grouped: set[str] = set()
    unpaid = b.inv.loc[[r.invoice_id for r in results if not r.right_id]].sort_values("invoice_date")
    spare = b.bank[b.bank["resolved_party_id"].notna() & ~b.bank.index.isin(used)].sort_values("txn_date")
    direction = {"PURCHASE": "DEBIT", "SALES": "CREDIT"}
    entries = _money_entries(b)
    booked_amounts = entries.dropna(subset=["target"]).groupby("target")["amount"].agg(list).to_dict()

    def open_invoices(party: str, kind: str, txn_date: pd.Timestamp) -> pd.DataFrame:
        days = (txn_date - unpaid["invoice_date"]).dt.days
        return unpaid[(unpaid["party_id"] == party) & (unpaid["invoice_type"] == kind) & days.between(-45, 120) & ~unpaid.index.isin(paid)]

    def spare_txns(party: str, kind: str, around: pd.Timestamp) -> pd.DataFrame:
        days = (spare["txn_date"] - around).dt.days.abs()
        return spare[(spare["resolved_party_id"] == party) & (spare["direction"] == direction[kind]) & (days <= 120) & ~spare.index.isin(used)]

    # One payment covering several invoices: the matcher took one, the rest add up to what is left of the payment.
    for invoice_id, txn_id in assigned.items():
        inv, txn = b.inv.loc[invoice_id], b.bank.loc[txn_id]
        excess = int(txn["amount_paise"]) - int(inv["invoice_total_paise"])
        if excess > TOLERANCE_PAISE:
            others = open_invoices(inv["party_id"], inv["invoice_type"], txn["txn_date"])
            others = others.loc[sorted(others.index, key=lambda i: not _quotes(txn["narration"], i))]
            hit = find_subset(others["invoice_total_paise"].astype(int).tolist(), excess, max_size=3)
            if hit:
                members = [invoice_id] + [others.index[i] for i in hit]
                for member in members:
                    paid[member] = [txn_id]
                groups.append((members, [txn_id]))
                grouped.update(members)

    # One invoice paid in parts: the matcher took one payment, spare payments make up the rest.
    for invoice_id, txn_id in assigned.items():
        if invoice_id in grouped:
            continue
        inv, txn = b.inv.loc[invoice_id], b.bank.loc[txn_id]
        short = int(inv["invoice_total_paise"]) - int(txn["amount_paise"])
        if short > TOLERANCE_PAISE:
            parts = spare_txns(inv["party_id"], inv["invoice_type"], txn["txn_date"])
            hit = find_subset(parts["amount_paise"].astype(int).tolist(), short, max_size=2)
            if hit:
                txns = [txn_id] + [parts.index[i] for i in hit]
                used.update(txns)
                paid[invoice_id] = txns
                groups.append(([invoice_id], txns))
                grouped.add(invoice_id)

    # Spare payments against invoices the matcher left open.
    for txn_id, txn in spare.iterrows():
        if txn_id in used or txn["direction"] not in direction.values():
            continue
        kind = "PURCHASE" if txn["direction"] == "DEBIT" else "SALES"
        others = open_invoices(txn["resolved_party_id"], kind, txn["txn_date"])
        others = others.loc[sorted(others.index, key=lambda i: not _quotes(txn["narration"], i))]
        hit = find_subset(others["invoice_total_paise"].astype(int).tolist(), int(txn["amount_paise"]), max_size=3)
        if hit:
            members = [others.index[i] for i in hit]
            used.add(txn_id)
            for member in members:
                paid[member] = [txn_id]
            groups.append((members, [txn_id]))
            grouped.update(members)

    matches: list[dict] = []
    for members, txns in groups:
        first = b.inv.loc[members[0]]
        total_inv = sum(int(b.inv.loc[m, "invoice_total_paise"]) for m in members)
        total_txn = sum(int(b.bank.loc[t, "amount_paise"]) for t in txns)
        what = f"{len(txns)} payments settle 1 invoice" if len(txns) > 1 else f"1 payment settles {len(members)} invoices"
        matches.append(match_row("payment", period_of(first["invoice_date"]), members, txns, "one_to_many", 0.95, "auto",
                                 [what, f"Invoices add up to {rupees(total_inv)}, payments to {rupees(total_txn)}", "Same Party, amounts agree to the rupee"]))
    for r in results:
        if r.invoice_id in grouped:
            continue
        inv = b.inv.loc[r.invoice_id]
        matches.append(match_row("payment", period_of(inv["invoice_date"]), [r.invoice_id], [r.right_id] if r.right_id else [], _layer(r), r.confidence, r.band, r.reasons))

    for invoice_id, txn_id in assigned.items():
        inv, txn = b.inv.loc[invoice_id], b.bank.loc[txn_id]
        r = by_invoice[invoice_id]
        common = dict(period=period_of(txn["txn_date"]), entity_id=txn_id, party_id=inv["party_id"], invoice_id=invoice_id, confidence=r.confidence,
                      refs=[("bank_transactions", txn_id), ("invoices", invoice_id)], left=bank_view(b, txn_id), right=invoice_view(b, invoice_id))
        gap = abs(int(txn["amount_paise"]) - int(inv["invoice_total_paise"]))
        # A first instalment is booked at the amount paid; a real mismatch is booked at the full invoice total.
        booked_as_paid = any(abs(a - int(txn["amount_paise"])) <= TOLERANCE_PAISE for a in booked_amounts.get(invoice_id, []))
        if invoice_id not in grouped and gap > TOLERANCE_PAISE and not booked_as_paid:
            findings.append(finding("PAYMENT_AMOUNT_MISMATCH", impact_type="unaccounted_payment", impact_paise=gap,
                                    title=f"Payment for {invoice_id} is {rupees(gap)} away from the invoice total",
                                    reason=f"The bank shows {rupees(txn['amount_paise'])} against an invoice of {rupees(inv['invoice_total_paise'])}, and the books record the full invoice amount as settled.",
                                    diffs=diff([("amount_paise", int(txn["amount_paise"]), int(inv["invoice_total_paise"]), None)]), **common))
        if txn["txn_date"] < inv["invoice_date"]:
            days = (inv["invoice_date"] - txn["txn_date"]).days
            findings.append(finding("PAYMENT_BEFORE_INVOICE", impact_type="none", impact_paise=int(txn["amount_paise"]),
                                    title=f"{invoice_id} was paid {days} days before its invoice date",
                                    reason=f"The payment is dated {nice_date(txn['txn_date'])} and the invoice {nice_date(inv['invoice_date'])}.",
                                    diffs=diff([("txn_date", txn["txn_date"], inv["invoice_date"], None)]), **common))
        if narration_id_tokens(txn["narration"]) and not _quotes(txn["narration"], invoice_id):
            quoted = ", ".join(narration_id_tokens(txn["narration"]))
            findings.append(finding("INVOICE_ID_MISMATCH", impact_type="none", impact_paise=0,
                                    title=f"Bank narration says {quoted}, the invoice is {invoice_id}",
                                    reason=f"The narration quotes {quoted}, which is not this invoice's number. Party, amount and date match {invoice_id}.",
                                    diffs=diff([("narration", txn["narration"], invoice_id, None)]), **common))

    # A spare payment equal to one that already settled an invoice is a second payment.
    paying = {t: i for i, txns in paid.items() for t in txns}
    for txn_id, txn in spare.iterrows():
        if txn_id in used:
            continue
        twins = [t for t in paying if b.bank.loc[t, "resolved_party_id"] == txn["resolved_party_id"] and b.bank.loc[t, "direction"] == txn["direction"]
                 and int(b.bank.loc[t, "amount_paise"]) == int(txn["amount_paise"]) and abs((b.bank.loc[t, "txn_date"] - txn["txn_date"]).days) <= 60]
        if twins:
            twin = twins[0]
            used.add(txn_id)
            findings.append(finding("DUPLICATE_PAYMENT", period=period_of(txn["txn_date"]), entity_id=txn_id, impact_type="unaccounted_payment", impact_paise=int(txn["amount_paise"]),
                                    title=f"{paying[twin]} was paid twice: {rupees(txn['amount_paise'])} extra",
                                    reason=f"Bank lines {twin} and {txn_id} carry the same amount for the same Party, and the invoice needs only one.",
                                    refs=[("bank_transactions", txn_id), ("bank_transactions", twin), ("invoices", paying[twin])],
                                    left=bank_view(b, txn_id), right=bank_view(b, twin), party_id=txn["resolved_party_id"], invoice_id=paying[twin]))

    left_over = spare[~spare.index.isin(used)]
    circular: set[str] = set()
    for txn_id, txn in left_over[left_over["direction"] == "DEBIT"].iterrows():
        if int(txn["amount_paise"]) % CIRCULAR_ROUND_PAISE:
            continue
        days = (left_over["txn_date"] - txn["txn_date"]).dt.days
        back = left_over[(left_over["direction"] == "CREDIT") & (left_over["resolved_party_id"] == txn["resolved_party_id"])
                         & (left_over["amount_paise"] == txn["amount_paise"]) & days.between(0, CIRCULAR_MAX_DAYS)]
        if back.empty:
            continue
        back_id = back.index[0]
        circular.update([txn_id, back_id])
        for this, other in ((txn_id, back_id), (back_id, txn_id)):
            row = b.bank.loc[this]
            findings.append(finding("CIRCULAR_FLOW", period=period_of(row["txn_date"]), entity_id=this, impact_type="none", impact_paise=int(row["amount_paise"]),
                                    title=f"{rupees(txn['amount_paise'])} went out to {b.parties.loc[txn['resolved_party_id'], 'party_name']} and came back",
                                    reason=f"{rupees(txn['amount_paise'])} left on {nice_date(txn['txn_date'])} with no invoice, and the same amount came back from the same Party on {nice_date(back.iloc[0]['txn_date'])}.",
                                    refs=[("bank_transactions", this), ("bank_transactions", other)], left=bank_view(b, this), right=bank_view(b, other),
                                    party_id=txn["resolved_party_id"], confidence=0.9))
    for txn_id, txn in left_over[~left_over.index.isin(circular)].iterrows():
        findings.append(finding("UNMATCHED_BANK_TXN", period=period_of(txn["txn_date"]), entity_id=txn_id, impact_type="unaccounted_payment", impact_paise=int(txn["amount_paise"]),
                                title=f"{rupees(txn['amount_paise'])} {'paid to' if txn['direction'] == 'DEBIT' else 'received from'} {b.parties.loc[txn['resolved_party_id'], 'party_name']} with no invoice",
                                reason="The Party is known, but no open invoice or group of invoices adds up to this amount.",
                                refs=[("bank_transactions", txn_id)], left=bank_view(b, txn_id), party_id=txn["resolved_party_id"], confidence=0.8))
    # Bank lines from nobody we know, with no ledger entry behind them (salaries, charges and tax payments are booked).
    booked_utrs = set(b.ledger["utr_ref"].dropna())
    for txn_id, txn in b.bank[b.bank["resolved_party_id"].isna() & ~b.bank["utr"].isin(booked_utrs)].iterrows():
        findings.append(finding("UNMATCHED_BANK_TXN", period=period_of(txn["txn_date"]), entity_id=txn_id, impact_type="unaccounted_payment", impact_paise=int(txn["amount_paise"]),
                                title=f"{rupees(txn['amount_paise'])} {'paid to' if txn['direction'] == 'DEBIT' else 'received from'} {txn['counterparty_name']} with no invoice or booking",
                                reason="The bank line quotes no invoice, the name is not in the party master and no ledger entry records it.",
                                refs=[("bank_transactions", txn_id)], left=bank_view(b, txn_id), confidence=0.8))

    # The ledger side of payments: mistyped references, entries made twice, and money booked that the bank never saw.
    seen: dict[tuple, str] = {}
    for entry_id, entry in entries.iterrows():
        invoice_id = entry["target"]
        if not invoice_id:
            continue
        common = dict(period=period_of(entry["posting_date"]), entity_id=entry_id, party_id=entry["party_id"], invoice_id=invoice_id,
                      left=ledger_view(b, entry_id), right=invoice_view(b, invoice_id), refs=[("ledger_entries", entry_id), ("invoices", invoice_id)])
        if entry["invoice_ref"] != invoice_id:
            findings.append(finding("INVOICE_ID_MISMATCH", impact_type="none", impact_paise=0,
                                    title=f"Ledger says {entry['invoice_ref']}, the invoice is {invoice_id}",
                                    reason=f"The {entry['voucher_type'].lower()} entry quotes {entry['invoice_ref']}. Party and amount match {invoice_id}.",
                                    diffs=diff([("invoice_ref", entry["invoice_ref"], invoice_id, None)]), confidence=0.85, **common))
        key = (entry["party_id"], invoice_id, entry["voucher_type"], entry["amount"])
        if key in seen:
            findings.append(finding("DUPLICATE_LEDGER_ENTRY", impact_type="unaccounted_payment", impact_paise=entry["amount"],
                                    title=f"The {entry['voucher_type'].lower()} for {invoice_id} is booked twice: {rupees(entry['amount'])}",
                                    reason=f"Ledger entries {seen[key]} and {entry_id} record the same {entry['voucher_type'].lower()} for the same invoice and amount.",
                                    **{**common, "right": ledger_view(b, seen[key]), "refs": [("ledger_entries", entry_id), ("ledger_entries", seen[key]), ("invoices", invoice_id)]}))
            continue
        seen[key] = entry_id
        if invoice_id not in paid:
            findings.append(finding("PAID_NOT_IN_BANK", impact_type="unaccounted_payment", impact_paise=entry["amount"],
                                    title=f"Books show {rupees(entry['amount'])} moved for {invoice_id}, the bank does not",
                                    reason=f"Ledger entry {entry_id} records a {entry['voucher_type'].lower()} for {invoice_id}, but no bank line from this Party matches it.",
                                    confidence=0.85, **common))
    return findings, matches, paid
