"""Rule-based Anomalies on invoices. Each one says why the Record looks unusual; none claims fraud."""
from __future__ import annotations

import pandas as pd

from .findings import Books, finding, invoice_view, nice_date, period_of, rupees

OUTLIER_TIMES = 8
SUNDAY_TIMES = 4
MIN_PARTY_HISTORY = 5
ROUND_MIN_PAISE = 1_00_000 * 100
ROUND_STEP_PAISE = 10_000 * 100
APPROVAL_LIMIT_PAISE = 2_00_000 * 100
SPLIT_MIN_SHARE = 0.90
SPLIT_DAYS = 4
SPLIT_MIN_INVOICES = 3
BURST_DAYS = 3
BURST_MIN_INVOICES = 6


def _clusters(group: pd.DataFrame, days: int, minimum: int) -> set[str]:
    """Invoice IDs that sit in a run of at least minimum invoices within the given number of days."""
    group = group.sort_values("invoice_date")
    dates = group["invoice_date"].tolist()
    ids = group.index.tolist()
    hit: set[str] = set()
    for i in range(len(ids)):
        j = i
        while j + 1 < len(ids) and (dates[j + 1] - dates[i]).days <= days:
            j += 1
        if j - i + 1 >= minimum:
            hit.update(ids[i:j + 1])
    return hit


def check(b: Books, aggregates: dict) -> list[dict]:
    out: list[dict] = []
    party_median = aggregates["party_median_taxable_paise"]
    party_count = aggregates["party_train_count"]
    category_median = aggregates["category_median_taxable_paise"]
    p95 = aggregates["taxable_p95_paise"]
    real = b.inv[b.inv["doc_type"] == "INVOICE"]

    def add(finding_type: str, invoice_id: str, title: str, reason: str) -> None:
        inv = b.inv.loc[invoice_id]
        out.append(finding(finding_type, period=period_of(inv["invoice_date"]), entity_id=invoice_id, impact_type="none", impact_paise=int(inv["invoice_total_paise"]),
                           title=title, reason=reason, refs=[("invoices", invoice_id)], left=invoice_view(b, invoice_id), party_id=inv["party_id"],
                           invoice_id=invoice_id, confidence=0.8))

    for invoice_id, inv in real.iterrows():
        taxable = int(inv["taxable_value_paise"])
        of_category = category_median.get(inv["category"]) or 0
        usual = party_median.get(inv["party_id"]) if party_count.get(inv["party_id"], 0) >= MIN_PARTY_HISTORY else of_category
        if taxable >= ROUND_MIN_PAISE and taxable % ROUND_STEP_PAISE == 0:
            add("ROUND_AMOUNT_SPIKE", invoice_id, f"{invoice_id} has a perfectly round value of {rupees(taxable)}",
                "Invoices for real goods and services rarely land on a large round figure.")
        elif inv["invoice_date"].dayofweek == 6 and usual and (taxable >= SUNDAY_TIMES * usual or taxable > p95):
            add("WEEKEND_LARGE_TXN", invoice_id, f"{invoice_id} for {rupees(taxable)} is dated on a Sunday",
                f"{nice_date(inv['invoice_date'])} is a Sunday, and the value is {taxable / usual:.0f} times this Party's usual invoice.")
        elif usual and of_category and taxable >= OUTLIER_TIMES * usual and taxable >= OUTLIER_TIMES * of_category:
            add("OUTLIER_AMOUNT", invoice_id, f"{invoice_id} is {taxable / usual:.0f} times {inv['party_name']}'s usual invoice",
                f"Taxable value {rupees(taxable)} against a usual {rupees(usual)} for this Party and {rupees(of_category)} for this item.")

    purchases = real[real["invoice_type"] == "PURCHASE"]
    near_limit = purchases[purchases["invoice_total_paise"].between(SPLIT_MIN_SHARE * APPROVAL_LIMIT_PAISE, APPROVAL_LIMIT_PAISE)]
    for party_id, group in near_limit.groupby("party_id"):
        members = _clusters(group, SPLIT_DAYS, SPLIT_MIN_INVOICES)
        for invoice_id in sorted(members):
            add("THRESHOLD_SPLITTING", invoice_id, f"{len(members)} invoices from {b.inv.loc[invoice_id, 'party_name']} sit just under the Rs 2,00,000 approval limit",
                f"Each is between 90 and 100 percent of the limit and they fall within {SPLIT_DAYS} days of each other: {', '.join(sorted(members))}.")
    for party_id, group in purchases.groupby("party_id"):
        small = group[group["taxable_value_paise"] < party_median.get(party_id, 0)]
        members = _clusters(small, BURST_DAYS, BURST_MIN_INVOICES)
        for invoice_id in sorted(members):
            add("VENDOR_BURST", invoice_id, f"{len(members)} small invoices from {b.inv.loc[invoice_id, 'party_name']} within {BURST_DAYS} days",
                f"This Supplier usually sends a few invoices a month. These came together, each below its usual value: {', '.join(sorted(members))}.")
    return out
