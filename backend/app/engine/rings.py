"""Supplier rings: Parties linked by one PAN, and the network graph for a Return period."""
from __future__ import annotations

import networkx as nx
import pandas as pd

from .findings import Books, finding, period_of, py, rupees


def pan_rings(b: Books) -> list[dict]:
    """Groups of Parties sharing a PAN that include at least one Supplier and one Customer."""
    graph = nx.Graph()
    for pan, group in b.parties.groupby("pan"):
        ids = group.index.tolist()
        graph.add_nodes_from(ids)
        graph.add_edges_from((ids[0], other) for other in ids[1:])
    rings = []
    for members in nx.connected_components(graph):
        types = set(b.parties.loc[list(members), "party_type"])
        if len(members) > 1 and {"VENDOR", "CUSTOMER"} <= types:
            rings.append({"members": sorted(members), "pan": b.parties.loc[sorted(members)[0], "pan"]})
    return rings


def party_view(b: Books, party_id: str) -> dict:
    party = b.parties.loc[party_id]
    return {"table": "parties", "id": party_id, "fields": {k: py(party[k]) for k in ("party_name", "party_type", "gstin", "pan", "state")}}


def check(b: Books) -> list[dict]:
    out: list[dict] = []
    for ring in pan_rings(b):
        suppliers = [m for m in ring["members"] if b.parties.loc[m, "party_type"] == "VENDOR"]
        customers = [m for m in ring["members"] if b.parties.loc[m, "party_type"] == "CUSTOMER"]
        names = " and ".join(b.parties.loc[m, "party_name"] for m in ring["members"])
        trade = b.inv[b.inv["party_id"].isin(ring["members"]) & (b.inv["doc_type"] == "INVOICE")]
        for period, group in trade.groupby(trade["invoice_date"].dt.strftime("%Y-%m")):
            bought = group[group["invoice_type"] == "PURCHASE"]
            sold = group[group["invoice_type"] == "SALES"]
            tax = int(bought["total_tax_paise"].sum())
            out.append(finding(
                "PAN_LINKED_RING", period=period, entity_id=suppliers[0], impact_type="itc_at_risk", impact_paise=tax,
                title=f"{names} share one PAN: {rupees(tax)} of credit depends on them",
                reason=(f"Both registrations carry PAN {ring['pan']}, so one owner is your Supplier and your Customer. This month you bought "
                        f"{rupees(bought['invoice_total_paise'].sum())} from one and sold {rupees(sold['invoice_total_paise'].sum())} to the other."),
                refs=[("parties", m) for m in ring["members"]] + [("invoices", i) for i in group.index],
                left=party_view(b, suppliers[0]), right=party_view(b, customers[0]), party_id=suppliers[0], confidence=0.9,
                impacts={i: {"igst": int(r["igst_paise"]), "cgst": int(r["cgst_paise"]), "sgst": int(r["sgst_paise"])} for i, r in bought.iterrows()}))
    return out


def graph(b: Books, period: str, findings: list[dict]) -> dict:
    """Nodes, edges and rings for the network view of one Return period. Every Party is a node; the page decides how many to draw."""
    month = b.inv[b.inv["invoice_date"].dt.strftime("%Y-%m") == period]
    volume = month.groupby("party_id")["invoice_total_paise"].sum().abs().sort_values(ascending=False)
    rings = pan_rings(b)
    ring_members = {m for ring in rings for m in ring["members"]}
    cancelled = set(b.parties.index[(b.parties["gstin_status"] == "cancelled")
                                    & (b.parties["cancelled_from"] <= pd.Period(period).end_time)]) & set(volume.index)
    flow_parties = {f["party_id"] for f in findings if f["finding_type"] == "CIRCULAR_FLOW"}
    keep = list(dict.fromkeys(list(ring_members) + sorted(cancelled) + sorted(flow_parties) + volume.index.tolist() + b.parties.index.tolist()))
    counts = month.groupby("party_id").size()

    nodes = [{"id": "company", "label": "Your company", "kind": "company", "risk": "clean", "volume_paise": 0, "invoice_count": 0}]
    edges = []
    for party_id in keep:
        party = b.parties.loc[party_id]
        risk = "ring" if party_id in ring_members else "cancelled" if party_id in cancelled else "clean"
        nodes.append({"id": party_id, "label": party["party_name"], "kind": "supplier" if party["party_type"] == "VENDOR" else "customer", "risk": risk,
                      "volume_paise": int(volume.get(party_id, 0)), "invoice_count": int(counts.get(party_id, 0))})
        edges.append({"source": "company", "target": party_id, "kind": "trade", "label": rupees(int(volume.get(party_id, 0)))})
    out_rings = []
    for n, ring in enumerate(rings, start=1):
        first = ring["members"][0]
        edges.extend({"source": first, "target": other, "kind": "same_pan", "label": f"Same PAN {ring['pan']}"} for other in ring["members"][1:])
        hits = [f for f in findings if f["finding_type"] == "PAN_LINKED_RING" and f["party_id"] in ring["members"]]
        flows = [f for f in findings if f["finding_type"] == "CIRCULAR_FLOW" and f["party_id"] in ring["members"]]
        reason = hits[0]["reason"] if hits else f"These Parties carry the same PAN {ring['pan']}."
        if flows:
            reason += " " + flows[0]["reason"]
        out_rings.append({"id": f"ring_{n}", "members": ring["members"], "reason": reason,
                          "itc_at_risk_paise": sum(f["impact_paise"] for f in hits),
                          "invoice_count": int(month["party_id"].isin(ring["members"]).sum())})
    for party_id in sorted(cancelled):
        party = b.parties.loc[party_id]
        hits = [f for f in findings if f["finding_type"] == "CANCELLED_GSTIN" and f["party_id"] == party_id]
        out_rings.append({"id": f"cancelled_{party_id}", "members": [party_id],
                          "reason": f"{party['party_name']}'s GSTIN {party['gstin']} is cancelled from {party['cancelled_from']:%d %b %Y}. Credit on invoices dated after that is at risk.",
                          "itc_at_risk_paise": sum(f["impact_paise"] for f in hits), "invoice_count": len(hits)})
    return {"nodes": nodes, "edges": edges, "rings": out_rings}
