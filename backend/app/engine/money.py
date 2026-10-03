"""ITC at risk, ITC found and Net payable for one Return period. Pure: numbers in, numbers out."""
from __future__ import annotations

from collections import Counter

from .findings import Books
from .labels import META, SEVERITY_ORDER

TAX_TYPES = ("igst", "cgst", "sgst")


def base(b: Books, period: str, matches: list[dict]) -> dict:
    """What the books and the filed return say for the period, before any Finding is applied."""
    month = b.inv[b.inv["invoice_date"].dt.strftime("%Y-%m") == period]
    sales, purchases = month[month["invoice_type"] == "SALES"], month[month["invoice_type"] == "PURCHASE"]
    filed = b.filings[b.filings["period"] == period]
    declared = None
    if not filed.empty:
        row = filed.iloc[0]
        declared = {"output_paise": int(row["total_output_tax_paise"]), "itc_paise": int(row["total_itc_claimed_paise"]),
                    "net_paise": int(row["net_tax_payable_paise"]), "filed_on": row["filing_date"].strftime("%Y-%m-%d"),
                    "due_on": row["due_date"].strftime("%Y-%m-%d")}
    counts = Counter()
    for match in matches:
        if match["period"] != period:
            continue
        if match["layer"] == "one_to_many":
            counts["one_to_many"] += 1
        elif match["kind"] == "payment" and match["band"] == "unmatched":
            counts["open"] += 1
        else:
            counts[match["band"]] += 1
    return {
        "period": period,
        "output": {t: int(sales[f"{t}_paise"].sum()) for t in TAX_TYPES},
        "itc": {t: int(purchases[f"{t}_paise"].sum()) for t in TAX_TYPES},
        "declared": declared,
        "invoice_count": int(len(month)),
        "match_counts": {k: int(counts.get(k, 0)) for k in ("auto", "review", "unmatched", "one_to_many", "open")},
    }


def _by_key(findings: list[dict]) -> dict[str, tuple[dict, dict]]:
    """For each invoice, the largest share any Finding puts on it, so two Findings on one invoice count once."""
    best: dict[str, tuple[dict, dict]] = {}
    for f in findings:
        for key, share in f["evidence"]["impacts"].items():
            if key not in best or sum(share.values()) > sum(best[key][0].values()):
                best[key] = (share, f)
    return best


IMPACT_RANK = {"itc_at_risk": 0, "itc_found": 0, "excess_tax": 0, "short_tax": 0, "unaccounted_payment": 1, "open_payable": 1, "none": 2}


def sort_key(f: dict) -> tuple:
    """Tax money first, then other money, then Findings with no Rupee impact; largest first within each."""
    return (IMPACT_RANK[f["impact_type"]], -f["impact_paise"], SEVERITY_ORDER[f["severity"]])


def summarise(base_figures: dict, findings: list[dict]) -> dict:
    """Headline numbers for the period from the base figures and the current status of each Finding."""
    live = [f for f in findings if f["status"] != "dismissed"]
    open_ = [f for f in live if f["status"] == "open"]
    approved = [f for f in live if f["status"] == "approved"]

    at_risk_open = _by_key([f for f in open_ if f["impact_type"] == "itc_at_risk"])
    by_cause: Counter = Counter()
    for share, f in at_risk_open.values():
        by_cause[f["finding_type"]] += sum(share.values())

    # Credit stays out of Eligible ITC until the Finding is dismissed; the filed return is judged separately.
    blocked = _by_key([f for f in live if f["impact_type"] == "itc_at_risk" and f["category"] != "filing"])
    by_type = []
    for t in TAX_TYPES:
        output = base_figures["output"][t]
        output -= sum(s.get(t, 0) for f in approved if f["impact_type"] == "excess_tax" for s in f["evidence"]["impacts"].values())
        output += sum(s.get(t, 0) for f in approved if f["impact_type"] == "short_tax" for s in f["evidence"]["impacts"].values())
        eligible = base_figures["itc"][t] - sum(share.get(t, 0) for share, _ in blocked.values())
        eligible += sum(s.get(t, 0) for f in approved if f["impact_type"] == "itc_found" for s in f["evidence"]["impacts"].values())
        by_type.append({"tax_type": t, "output_paise": output, "eligible_itc_paise": eligible, "net_paise": output - eligible})

    def total(impact_type: str) -> int:
        return sum(f["impact_paise"] for f in open_ if f["impact_type"] == impact_type)

    net = sum(row["net_paise"] for row in by_type)
    declared = base_figures["declared"]
    return {
        "period": base_figures["period"],
        "itc_at_risk_paise": sum(sum(share.values()) for share, _ in at_risk_open.values()),
        "itc_found_paise": total("itc_found"),
        "excess_tax_paise": total("excess_tax"),
        "short_tax_paise": total("short_tax"),
        "net_payable_paise": net,
        "invoice_count": base_figures["invoice_count"],
        "match_counts": base_figures["match_counts"],
        "finding_counts_by_category": dict(Counter(f["category"] for f in open_)),
        "finding_counts_by_status": dict(Counter(f["status"] for f in findings)),
        "itc_at_risk_by_cause": [{"finding_type": k, "label": META[k][0], "paise": v} for k, v in by_cause.most_common()],
        "top_findings": sorted(open_, key=sort_key)[:5],
        "liability": {"by_tax_type": by_type, "declared": declared, "gap_paise": None if declared is None else net - declared["net_paise"],
                      "simplified_setoff": True},
    }
