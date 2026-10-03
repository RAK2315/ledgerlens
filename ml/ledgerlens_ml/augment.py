"""Generate GSTR-2B lines and the extra Ground truth the workbook lacks (ML_BUILD.md 3.5). Deterministic."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .data import GSTR2B_COLUMNS, LABEL_COLUMNS, Dataset, gstin_check_char, money_name
from .parties import resolve_bank

ID_VARIANTS = ("digits_only", "slash", "inv_prefix")


@dataclass(frozen=True)
class Augmentation:
    gstr2b: pd.DataFrame
    labels: pd.DataFrame
    manifest: dict


def supplier_format(invoice_id: str, variant: str) -> str:
    """Rewrite VEN001-0001 the way a supplier might number it on their own return."""
    code, serial = invoice_id.split("-")
    if variant == "digits_only":
        return str(int(serial))
    if variant == "slash":
        return f"{code[:3]}/{code[3:]}/{serial}"
    return f"INV-{serial}"


def _split_tax(taxable_paise: int, rate_pct: int, interstate: bool) -> tuple[int, int, int]:
    """Return (igst, cgst, sgst) in paise for a taxable value, half up."""
    tax = (taxable_paise * rate_pct + 50) // 100
    if interstate:
        return tax, 0, 0
    cgst = (tax + 1) // 2
    return 0, cgst, tax - cgst


def _ring_supplier(ds: Dataset, rng: np.random.Generator, suppliers: list[str]) -> str:
    """The supplier behind the earliest circular flow, so the ring has a round trip to show."""
    flows = ds.labels[(ds.labels["issue_type"] == "CIRCULAR_FLOW")]
    bank = resolve_bank(ds.bank, ds.parties, ds.invoices)
    bank = bank[bank["txn_id"].isin(flows["entity_id"]) & bank["resolved_party_id"].isin(suppliers)]
    if bank.empty:
        return str(rng.choice(suppliers))
    return bank.sort_values(["txn_date", "txn_id"]).iloc[0]["resolved_party_id"]


def _filing_behaviour(rng: np.random.Generator, suppliers: list[str], ring_supplier: str) -> dict[str, str]:
    others = [s for s in suppliers if s != ring_supplier]
    shuffled = [others[i] for i in rng.permutation(len(others))]
    late = round(len(suppliers) * dict(config.AUGMENT_FILING_BEHAVIOUR)["late"])
    non_filer = round(len(suppliers) * dict(config.AUGMENT_FILING_BEHAVIOUR)["non_filer"])
    behaviour = {ring_supplier: "reliable"}
    for i, party_id in enumerate(shuffled):
        behaviour[party_id] = "non_filer" if i < non_filer else "late" if i < non_filer + late else "reliable"
    return dict(sorted(behaviour.items()))


def _label(issue_type: str, category: str, severity: str, entity_type: str, entity_id: str, field: str,
           description: str, impact_paise: int | None = None, related: str | None = None,
           expected: str | None = None, recorded: str | None = None) -> dict:
    return {
        "issue_type": issue_type, "issue_category": category, "severity": severity, "entity_type": entity_type,
        "entity_id": entity_id, "related_entity_id": related, "field_affected": field, "expected_value": expected,
        "recorded_value": recorded, "financial_impact_paise": impact_paise, "description": description,
        "is_benign": False, "source": "augment",
    }


def build_augmentation(ds: Dataset, seed: int = config.SEED) -> Augmentation:
    rng = np.random.default_rng(seed)
    parties = ds.parties.sort_values("party_id").set_index("party_id")
    suppliers = parties.index[parties["party_type"] == "VENDOR"].tolist()
    customers = parties.index[parties["party_type"] == "CUSTOMER"].tolist()
    purchases = ds.invoices[(ds.invoices["invoice_type"] == "PURCHASE") & (ds.invoices["doc_type"] == "INVOICE")]
    purchases = purchases.sort_values(["invoice_date", "invoice_id"]).reset_index(drop=True)
    labels: list[dict] = []

    ring_supplier = _ring_supplier(ds, rng, suppliers)
    ring_customer = str(rng.choice(customers))
    behaviour = _filing_behaviour(rng, suppliers, ring_supplier)

    # The supplier issued a duplicated purchase invoice once, so the copy in the books has no line.
    duplicate_labels = ds.labels[(ds.labels["issue_type"] == "DUPLICATE_INVOICE") & (ds.labels["source"] == "workbook")]
    duplicates = sorted(set(duplicate_labels["entity_id"]) & set(purchases["invoice_id"]))

    n = len(purchases)
    draws = {
        "variant": rng.random(n), "variant_kind": rng.integers(0, len(ID_VARIANTS), n),
        "value": rng.random(n), "value_frac": rng.uniform(*config.AUGMENT_VALUE_MISMATCH_RANGE, n),
        "value_sign": rng.choice([-1, 1], n), "date": rng.random(n),
        "date_days": rng.integers(config.AUGMENT_DATE_SHIFT_DAYS[0], config.AUGMENT_DATE_SHIFT_DAYS[1] + 1, n),
    }
    counts = {"id_variants": 0, "value_mismatches": 0, "date_shifts": 0}
    lines: list[dict] = []
    for i, inv in enumerate(purchases.itertuples()):
        filing = behaviour[inv.party_id]
        if inv.invoice_id in duplicates:
            continue
        if filing == "non_filer":
            labels.append(_label("MISSING_IN_2B", "MISSING", "High", "INVOICE", inv.invoice_id, "gstr2b_line",
                                 "Supplier did not report this invoice in GSTR-1, so it is absent from GSTR-2B",
                                 impact_paise=inv.total_tax_paise, expected="line present", recorded="no line"))
            continue
        number, date = inv.invoice_id, inv.invoice_date
        taxable, igst, cgst, sgst = inv.taxable_value_paise, inv.igst_paise, inv.cgst_paise, inv.sgst_paise
        if draws["variant"][i] < config.AUGMENT_ID_VARIANT_RATE:
            number = supplier_format(inv.invoice_id, ID_VARIANTS[draws["variant_kind"][i]])
            counts["id_variants"] += 1
        if draws["value"][i] < config.AUGMENT_VALUE_MISMATCH_RATE:
            factor = 1 + draws["value_sign"][i] * draws["value_frac"][i]
            taxable = int(round(taxable * factor))
            igst, cgst, sgst = (int(round(x * factor)) for x in (igst, cgst, sgst))
            counts["value_mismatches"] += 1
            labels.append(_label("GSTR2B_VALUE_MISMATCH", "MISSING", "Medium", "INVOICE", inv.invoice_id, "taxable_value",
                                 "Supplier reported a different taxable value in GSTR-2B than the invoice in the books",
                                 impact_paise=abs(inv.total_tax_paise - (igst + cgst + sgst)),
                                 expected=str(inv.taxable_value_paise), recorded=str(taxable)))
        if draws["date"][i] < config.AUGMENT_DATE_SHIFT_RATE:
            date = date + pd.Timedelta(days=int(draws["date_days"][i]))
            counts["date_shifts"] += 1
        invoice_month = inv.invoice_date.to_period("M")
        period = invoice_month + 1 if filing == "late" else min(date.to_period("M"), invoice_month + 1)
        if period != invoice_month:
            why = "Supplier filed late, so the line sits in the next Return period" if filing == "late" else "Supplier dated the invoice in the next month"
            labels.append(_label("PERIOD_SHIFT", "MISSING", "Low", "INVOICE", inv.invoice_id, "return_period", why,
                                 expected=str(invoice_month), recorded=str(period)))
        lines.append({
            "gstin_supplier": parties.at[inv.party_id, "gstin"], "trade_name": parties.at[inv.party_id, "party_name"],
            "invoice_number": number, "invoice_date": date, "invoice_value_paise": taxable + igst + cgst + sgst,
            "place_of_supply": inv.place_of_supply, "rate": inv.tax_rate_pct, "taxable_value_paise": taxable,
            "igst_paise": igst, "cgst_paise": cgst, "sgst_paise": sgst, "period": period,
            "source_invoice_id": inv.invoice_id,
        })

    # Supplies the supplier reported that never reached the books: ITC found.
    filed = purchases[purchases["party_id"].map(behaviour) != "non_filer"].reset_index(drop=True)
    n_extra = round(config.AUGMENT_EXTRA_LINE_RATE * n)
    sources = filed.iloc[np.sort(rng.choice(len(filed), size=n_extra, replace=False))]
    day_offsets = rng.integers(1, 6, n_extra)
    scales = rng.uniform(0.7, 1.3, n_extra)
    next_serial = purchases.groupby("party_id")["invoice_id"].agg(lambda ids: max(int(x.split("-")[1]) for x in ids) + 1).to_dict()
    fy_end = pd.Timestamp(config.FY_END)
    for src, offset, scale in zip(sources.itertuples(), day_offsets, scales):
        date = min(src.invoice_date + pd.Timedelta(days=int(offset)), fy_end)
        taxable = int(round(src.taxable_value_paise * scale))
        igst, cgst, sgst = _split_tax(taxable, src.tax_rate_pct, interstate=src.igst_paise > 0)
        number = f"{src.invoice_id.split('-')[0]}-{next_serial[src.party_id]:04d}"
        next_serial[src.party_id] += 1
        lines.append({
            "gstin_supplier": parties.at[src.party_id, "gstin"], "trade_name": parties.at[src.party_id, "party_name"],
            "invoice_number": number, "invoice_date": date, "invoice_value_paise": taxable + igst + cgst + sgst,
            "place_of_supply": src.place_of_supply, "rate": src.tax_rate_pct, "taxable_value_paise": taxable,
            "igst_paise": igst, "cgst_paise": cgst, "sgst_paise": sgst, "period": date.to_period("M"),
            "source_invoice_id": None,
        })

    gstr2b = pd.DataFrame(lines).sort_values(["period", "gstin_supplier", "invoice_date", "invoice_number"], kind="stable").reset_index(drop=True)
    gstr2b["line_id"] = [f"2B-{i:06d}" for i in range(1, len(gstr2b) + 1)]
    gstr2b["return_period"] = gstr2b["period"].dt.strftime("%m%Y")
    gstr2b = gstr2b.assign(invoice_type="R", reverse_charge="N", cess_paise=0, itc_availability="Y", reason=None)
    for line in gstr2b[gstr2b["source_invoice_id"].isna()].itertuples():
        labels.append(_label("MISSING_IN_BOOKS", "MISSING", "Medium", "GSTR2B_LINE", line.line_id, "invoice",
                             "Supplier reported this supply in GSTR-2B but no invoice for it is in the books",
                             impact_paise=line.igst_paise + line.cgst_paise + line.sgst_paise,
                             expected="invoice booked", recorded="no invoice"))
    gstr2b = gstr2b[[money_name(c) if kind.rstrip("?") == "money" else c for c, kind in GSTR2B_COLUMNS.items()]]
    gstr2b = gstr2b.astype({"source_invoice_id": "object", "reason": "object"})

    unpaid = set(ds.links.loc[ds.links["link_type"] == "UNPAID_OPEN", "invoice_id"])
    cutoff = pd.Timestamp(config.FY_END) - pd.Timedelta(days=config.RULE_37_DAYS)
    for inv in purchases[purchases["invoice_id"].isin(unpaid) & (purchases["invoice_date"] < cutoff)].itertuples():
        labels.append(_label("RULE_37_UNPAID_180", "TAX", "Critical", "INVOICE", inv.invoice_id, "payment",
                             f"Supplier unpaid for more than {config.RULE_37_DAYS} days as of {config.FY_END}",
                             impact_paise=inv.total_tax_paise, expected=f"paid within {config.RULE_37_DAYS} days", recorded="unpaid"))

    per_supplier = purchases.groupby("party_id").size()
    non_filers = [p for p in suppliers if behaviour[p] == "non_filer" and per_supplier.get(p, 0) >= 2]
    cancelled = []
    for party_id in sorted(non_filers, key=lambda p: (-per_supplier.get(p, 0), p))[: config.AUGMENT_CANCELLED_SUPPLIERS]:
        theirs = purchases[purchases["party_id"] == party_id]
        cancelled_from = theirs["invoice_date"].iloc[len(theirs) // 2]
        cancelled.append({"party_id": party_id, "gstin": parties.at[party_id, "gstin"], "cancelled_from": cancelled_from.strftime("%Y-%m-%d")})
        for inv in theirs[theirs["invoice_date"] >= cancelled_from].itertuples():
            labels.append(_label("CANCELLED_GSTIN", "TAX", "Critical", "INVOICE", inv.invoice_id, "party_gstin",
                                 "Invoice dated on or after the day the supplier's GSTIN was cancelled",
                                 impact_paise=inv.total_tax_paise, expected="active GSTIN", recorded=f"cancelled from {cancelled_from:%Y-%m-%d}"))

    shared_pan = parties.at[ring_supplier, "pan"]
    old_gstin = parties.at[ring_customer, "gstin"]
    first14 = old_gstin[:2] + shared_pan + old_gstin[12:14]
    ring = {
        "supplier_party_id": ring_supplier, "customer_party_id": ring_customer, "shared_pan": shared_pan,
        "old_pan": parties.at[ring_customer, "pan"], "new_pan": shared_pan,
        "old_gstin": old_gstin, "new_gstin": first14 + gstin_check_char(first14),
    }
    for party_id, other in ((ring_supplier, ring_customer), (ring_customer, ring_supplier)):
        labels.append(_label("PAN_LINKED_RING", "ANOMALY", "Critical", "PARTY", party_id, "pan",
                             "Supplier and customer registrations carry the same PAN", related=other,
                             expected="unrelated parties", recorded=shared_pan))

    label_frame = pd.DataFrame(labels)
    label_frame.insert(0, "issue_id", [f"AUG-{i:04d}" for i in range(1, len(label_frame) + 1)])
    label_frame = label_frame[[money_name(c) if kind.rstrip("?") == "money" else c for c, kind in LABEL_COLUMNS.items()]]
    label_frame["financial_impact_paise"] = label_frame["financial_impact_paise"].astype("Int64")

    manifest = {
        "seed": seed,
        "source_sha256": ds.sha256,
        "rates": {
            "filing_behaviour": dict(config.AUGMENT_FILING_BEHAVIOUR),
            "id_variant": config.AUGMENT_ID_VARIANT_RATE,
            "value_mismatch": config.AUGMENT_VALUE_MISMATCH_RATE,
            "date_shift": config.AUGMENT_DATE_SHIFT_RATE,
            "extra_lines": config.AUGMENT_EXTRA_LINE_RATE,
        },
        "counts": {**counts, "purchase_invoices": n, "gstr2b_lines": len(gstr2b), "extra_lines": n_extra,
                   "labels": label_frame["issue_type"].value_counts().sort_index().to_dict()},
        "filing_behaviour": behaviour,
        "duplicate_invoices_skipped": duplicates,
        "cancelled_suppliers": cancelled,
        "pan_rings": [ring],
    }
    manifest = json.loads(json.dumps(manifest))
    return Augmentation(gstr2b=gstr2b, labels=label_frame, manifest=manifest)


def _rupees(paise: object) -> str:
    if pd.isna(paise):
        return ""
    paise = int(paise)
    sign, paise = ("-" if paise < 0 else ""), abs(paise)
    return f"{sign}{paise // 100}.{paise % 100:02d}"


def _to_csv(frame: pd.DataFrame, contract: dict[str, str], path: Path) -> None:
    """Write a typed frame in the contract's file columns: money back in rupees, dates as ISO text."""
    out = {}
    for column, kind in contract.items():
        kind = kind.rstrip("?")
        if kind == "money":
            out[column] = frame[money_name(column)].map(_rupees)
        elif kind == "date":
            out[column] = frame[column].dt.strftime("%Y-%m-%d")
        else:
            out[column] = frame[column]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        pd.DataFrame(out).to_csv(handle, index=False, lineterminator="\n")


def write_augmentation(aug: Augmentation, out_dir: str | Path | None = None) -> Path:
    out_dir = Path(out_dir) if out_dir is not None else config.DERIVED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    _to_csv(aug.gstr2b, GSTR2B_COLUMNS, out_dir / "gstr2b.csv")
    _to_csv(aug.labels, LABEL_COLUMNS, out_dir / "augment_labels.csv")
    (out_dir / "augment_manifest.json").write_text(json.dumps(aug.manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out_dir
