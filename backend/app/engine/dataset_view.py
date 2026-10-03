"""What the Data page shows about the dataset: its sheets, what was planted in it, and how GSTR-2B was generated."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from . import analyse
from .labels import META

# Plain names for the label types the engine has no Finding type for.
NAMES = {
    "LEGIT_OPEN_INVOICE": "Invoice still open, not yet paid",
    "PARTIAL_PAYMENT": "Invoice paid in instalments",
    "ROUNDING_NOISE": "Rounding difference under a rupee",
    "BUNDLED_PAYMENT": "One payment for two invoices",
    "CREDIT_NOTE": "Credit note against an earlier invoice",
    "NON_INVOICE_TXN": "Bank item that needs no invoice",
    "ITC_ON_DUPLICATE_INVOICE": "Credit claimed on a duplicate invoice",
}
SHEETS = ("invoices", "ledger", "bank", "gstr2b", "parties", "tax_rates", "filings", "links", "answer_key")


def _clean(value):
    """A label cell as JSON: missing values become None."""
    return None if pd.isna(value) else value


def overview() -> dict:
    ds = analyse.dataset()
    planted = []
    for (issue_type, source), group in ds.labels.groupby(["issue_type", "source"], sort=False):
        first = group.iloc[0]
        planted.append({
            "issue_type": issue_type,
            "label": NAMES.get(issue_type) or (META[issue_type][0] if issue_type in META else issue_type.replace("_", " ").capitalize()),
            "category": str(first["issue_category"]).lower(),
            "source": source,
            "benign": bool(first["is_benign"]),
            "count": int(len(group)),
            "example": {"entity_type": str(first["entity_type"]).lower(), "entity_id": first["entity_id"], "field": _clean(first["field_affected"]),
                        "expected": _clean(first["expected_value"]), "recorded": _clean(first["recorded_value"]),
                        "description": _clean(first["description"]), "impact_paise": int(_clean(first["financial_impact_paise"]) or 0)},
        })
    planted.sort(key=lambda p: (p["benign"], p["source"] != "workbook", -p["count"]))
    manifest = ds.manifest
    return {
        "sha256": ds.sha256,
        "sheets": [{"name": name, "rows": int(len(getattr(ds, name)))} for name in SHEETS],
        "workbook_labels": int((ds.labels["source"] == "workbook").sum()),
        "planted": planted,
        "gstr2b": {"seed": manifest["seed"], "rates": manifest["rates"], "counts": manifest["counts"],
                   "behaviours": dict(Counter(manifest["filing_behaviour"].values()))},
    }
