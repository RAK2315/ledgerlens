"""What the Ring view shows beyond the graph: one Party's month, the money moving through a ring, and the ring across the year."""
from __future__ import annotations

from .engine import rings
from .engine.findings import Books, py, rupees


def _month(frame, column: str, period: str):
    return frame[frame[column].dt.strftime("%Y-%m") == period]


def party(b: Books, period: str, party_id: str) -> dict | None:
    """A Party with its invoices and bank lines for the Return period."""
    if party_id not in b.parties.index:
        return None
    p = b.parties.loc[party_id]
    invoices = _month(b.inv[b.inv["party_id"] == party_id], "invoice_date", period).sort_values("invoice_date")
    lines = b.bank[b.bank["resolved_party_id"] == party_id]
    month_lines = _month(lines, "txn_date", period).sort_values("txn_date")
    return {
        "party": {"id": party_id, "name": p["party_name"], "kind": "supplier" if p["party_type"] == "VENDOR" else "customer", "gstin": p["gstin"], "pan": p["pan"],
                  "state": p["state"], "gstin_status": p["gstin_status"], "cancelled_from": py(p["cancelled_from"]), "filing_behaviour": py(p["filing_behaviour"]),
                  "bank_account": py(lines["counterparty_account"].iloc[0]) if len(lines) else None},
        "invoices": [{"id": i, "date": py(r["invoice_date"]), "doc_type": r["doc_type"].lower(), "total_paise": int(r["invoice_total_paise"]), "tax_paise": int(r["total_tax_paise"])}
                     for i, r in invoices.iterrows()],
        "payments": [{"id": i, "date": py(r["txn_date"]), "direction": r["direction"].lower(), "amount_paise": int(r["amount_paise"]), "narration": r["narration"]}
                     for i, r in month_lines.iterrows()],
    }


def shared_accounts(b: Books) -> list[dict]:
    """Bank accounts used by more than one Party."""
    known = b.bank.dropna(subset=["resolved_party_id"])
    groups = known.groupby("counterparty_account")["resolved_party_id"].unique()
    return [{"account": account, "members": sorted(members)} for account, members in groups.items() if len(members) > 1]


def _trade_step(b: Books, kind: str, party_id: str, frame) -> dict:
    total = int(frame["invoice_total_paise"].sum())
    verb, side = ("bought", "from") if kind == "purchase" else ("sold", "to")
    plural = "" if len(frame) == 1 else "s"
    return {"kind": kind, "party_id": party_id, "date": py(frame["invoice_date"].min()), "until": py(frame["invoice_date"].max()), "amount_paise": total,
            "records": frame.index.tolist(), "text": f"You {verb} {rupees(total)} {side} {b.parties.loc[party_id, 'party_name']} on {len(frame)} invoice{plural}."}


def _flow_step(b: Books, txn_id: str) -> dict:
    line = b.bank.loc[txn_id]
    out = line["direction"] == "DEBIT"
    phrase = "went out to" if out else "came back from"
    return {"kind": "out" if out else "back", "party_id": line["resolved_party_id"], "date": py(line["txn_date"]), "until": None, "amount_paise": int(line["amount_paise"]),
            "records": [txn_id], "text": f"{rupees(line['amount_paise'])} {phrase} {b.parties.loc[line['resolved_party_id'], 'party_name']} with no invoice."}


def stories(b: Books, period: str, flows: list[dict]) -> list[dict]:
    """For each PAN ring: the month's money in dated steps, and what depended on the ring in every month. flows are the year's round trips."""
    out = []
    for n, ring in enumerate(rings.pan_rings(b), start=1):
        members = ring["members"]
        supplier = next(m for m in members if b.parties.loc[m, "party_type"] == "VENDOR")
        customer = next(m for m in members if b.parties.loc[m, "party_type"] == "CUSTOMER")
        trade = b.inv[b.inv["party_id"].isin(members) & (b.inv["doc_type"] == "INVOICE")]
        month = _month(trade, "invoice_date", period)
        steps = [_trade_step(b, kind, party_id, frame)
                 for kind, party_id, frame in (("purchase", supplier, month[month["invoice_type"] == "PURCHASE"]), ("sale", customer, month[month["invoice_type"] == "SALES"]))
                 if len(frame)]
        mine = [f for f in flows if f["party_id"] in members]
        legs = {r["id"] for f in mine if f["period"] == period for r in f["record_refs"] if r["table"] == "bank_transactions"}
        steps += [_flow_step(b, txn_id) for txn_id in sorted(legs, key=lambda i: b.bank.loc[i, "txn_date"])]

        round_trips = {f["period"] for f in mine}
        timeline = []
        for month_period, group in trade.groupby(trade["invoice_date"].dt.strftime("%Y-%m")):
            bought = group[group["invoice_type"] == "PURCHASE"]
            timeline.append({"period": month_period, "bought_paise": int(bought["invoice_total_paise"].sum()),
                             "sold_paise": int(group.loc[group["invoice_type"] == "SALES", "invoice_total_paise"].sum()),
                             "credit_paise": int(bought["total_tax_paise"].sum()), "round_trip": month_period in round_trips})
        name = b.parties["party_name"]
        out.append({"ring_id": f"ring_{n}", "pan": ring["pan"], "supplier": {"id": supplier, "name": name[supplier]}, "customer": {"id": customer, "name": name[customer]},
                    "steps": steps, "timeline": timeline})
    return out
