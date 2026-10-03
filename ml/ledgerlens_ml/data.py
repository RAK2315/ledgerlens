"""Load and validate the workbook. The only module that reads it; everything else gets typed frames."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Sheet name to (column, kind). Kinds: str, int, money, date, datetime, bool. A trailing ? means nullable.
SHEETS: dict[str, dict[str, str]] = {
    "invoices": {
        "invoice_id": "str", "doc_type": "str", "invoice_type": "str", "invoice_date": "date",
        "due_date": "date?", "party_id": "str", "party_name": "str", "party_gstin": "str",
        "party_state_code": "int", "place_of_supply": "int", "hsn_sac": "int", "category": "str",
        "taxable_value": "money", "tax_rate_pct": "int", "cgst": "money", "sgst": "money",
        "igst": "money", "total_tax": "money", "invoice_total": "money", "currency": "str",
        "original_invoice_id": "str?",
    },
    "bank_transactions": {
        "txn_id": "str", "txn_date": "date", "value_date": "date", "bank_account": "str",
        "direction": "str", "amount": "money", "currency": "str", "counterparty_name": "str",
        "counterparty_account": "str", "payment_mode": "str", "utr": "str", "narration": "str",
        "closing_balance": "money",
    },
    "accounting_ledger": {
        "entry_id": "str", "voucher_no": "str", "posting_date": "date", "fiscal_period": "str",
        "voucher_type": "str", "ledger_account": "str", "party_id": "str?", "party_name": "str?",
        "invoice_ref": "str?", "taxable_amount": "money?", "cgst": "money?", "sgst": "money?",
        "igst": "money?", "total_tax": "money?", "total_amount": "money", "debit": "money",
        "credit": "money", "utr_ref": "str?", "narration": "str", "entered_by": "str",
        "entry_timestamp": "datetime",
    },
    "tax_rates": {
        "category_code": "str", "category": "str", "hsn_sac": "int", "supply_type": "str",
        "gst_rate_pct": "int", "cgst_pct": "float", "sgst_pct": "float", "igst_pct": "int",
        "effective_from": "date", "effective_to": "date?", "is_exempt": "bool",
    },
    "party_master": {
        "party_id": "str", "party_name": "str", "party_type": "str", "gstin": "str", "pan": "str",
        "state_code": "int", "state": "str", "payment_terms_days": "int",
    },
    "tax_filings": {
        "period": "str", "return_type": "str", "due_date": "date", "filing_date": "date",
        "outward_taxable_value": "money", "output_cgst": "money", "output_sgst": "money",
        "output_igst": "money", "total_output_tax": "money", "itc_cgst": "money", "itc_sgst": "money",
        "itc_igst": "money", "total_itc_claimed": "money", "net_tax_payable": "money", "status": "str",
    },
    "answer_key": {
        "period": "str", "true_outward_taxable_value": "money", "true_output_tax": "money",
        "true_eligible_itc": "money", "itc_blocked_invalid_supplier_gstin": "money",
        "true_net_tax_liability": "money", "declared_total_output_tax": "money",
        "declared_total_itc": "money", "declared_net_tax_payable": "money", "liability_gap_inr": "money",
    },
    "labels": {
        "issue_id": "str", "issue_type": "str", "issue_category": "str", "severity": "str?",
        "entity_type": "str", "entity_id": "str", "related_entity_id": "str?", "field_affected": "str",
        "expected_value": "str?", "recorded_value": "str?", "financial_impact_inr": "money?",
        "description": "str", "is_benign": "bool",
    },
    "links": {
        "invoice_id": "str", "booking_entry_id": "str?", "txn_id": "str?", "receipt_entry_id": "str?",
        "allocated_amount": "money", "link_type": "str",
    },
}

GSTR2B_COLUMNS: dict[str, str] = {
    "line_id": "str", "gstin_supplier": "str", "trade_name": "str", "invoice_number": "str",
    "invoice_type": "str", "invoice_date": "date", "invoice_value": "money", "place_of_supply": "int",
    "reverse_charge": "str", "rate": "int", "taxable_value": "money", "igst": "money", "cgst": "money",
    "sgst": "money", "cess": "money", "return_period": "str", "itc_availability": "str",
    "reason": "str?", "source_invoice_id": "str?",
}

LABEL_COLUMNS = {**SHEETS["labels"], "source": "str"}


class DatasetError(Exception):
    """The workbook or a derived file does not match the contract."""


@dataclass(frozen=True)
class Dataset:
    invoices: pd.DataFrame
    bank: pd.DataFrame
    ledger: pd.DataFrame
    tax_rates: pd.DataFrame
    parties: pd.DataFrame
    filings: pd.DataFrame
    answer_key: pd.DataFrame
    labels: pd.DataFrame
    links: pd.DataFrame
    gstr2b: pd.DataFrame | None
    manifest: dict | None
    sha256: str


def to_paise(values: pd.Series) -> pd.Series:
    """Rupees to integer paise, round half up. Nulls stay null (nullable Int64)."""
    rupees = pd.to_numeric(values, errors="raise").astype("float64")
    paise = np.sign(rupees) * np.floor(np.abs(rupees) * 100 + 0.5 + 1e-6)
    if rupees.isna().any():
        return pd.Series(paise, index=values.index).astype("Int64")
    return pd.Series(paise, index=values.index).astype("int64")


def money_name(column: str) -> str:
    return column.removesuffix("_inr") + "_paise"


def gstin_check_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        product = GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return GSTIN_CHARS[(36 - total % 36) % 36]


def is_valid_gstin(gstin: object) -> bool:
    if not isinstance(gstin, str) or len(gstin) != 15:
        return False
    if not gstin[:2].isdigit() or any(ch not in GSTIN_CHARS for ch in gstin):
        return False
    return gstin_check_char(gstin[:14]) == gstin[14]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def typed_frame(raw: pd.DataFrame, contract: dict[str, str], name: str) -> pd.DataFrame:
    """Check columns against the contract and convert each to its type."""
    expected, actual = list(contract), list(raw.columns)
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    if missing or extra:
        raise DatasetError(f"{name}: missing columns {missing}, unknown columns {extra}")
    out: dict[str, pd.Series] = {}
    for column, kind in contract.items():
        nullable = kind.endswith("?")
        kind = kind.rstrip("?")
        values = raw[column]
        if not nullable and values.isna().any():
            raise DatasetError(f"{name}.{column}: {int(values.isna().sum())} null values in a required column")
        if kind == "str":
            out[column] = values.map(lambda v: None if pd.isna(v) else str(v)).astype("object")
        elif kind == "int":
            out[column] = pd.to_numeric(values, errors="raise").astype("int64")
        elif kind == "float":
            out[column] = pd.to_numeric(values, errors="raise").astype("float64")
        elif kind == "bool":
            out[column] = values.astype(str).str.lower().isin(["true", "1"]) if values.dtype == object else values.astype(bool)
        elif kind == "money":
            out[money_name(column)] = to_paise(values)
        elif kind == "date":
            out[column] = pd.to_datetime(values, errors="raise").dt.normalize()
        elif kind == "datetime":
            out[column] = pd.to_datetime(values, errors="raise")
        else:
            raise DatasetError(f"{name}.{column}: unknown kind {kind}")
    return pd.DataFrame(out)


def read_gstr2b(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    return typed_frame(raw, GSTR2B_COLUMNS, "gstr2b")


def read_augment_labels(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    return typed_frame(raw, LABEL_COLUMNS, "augment_labels")


def apply_manifest(parties: pd.DataFrame, invoices: pd.DataFrame, manifest: dict | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add filing behaviour, cancelled GSTINs and the PAN ring from the augmentation to the party frames."""
    parties = parties.copy()
    invoices = invoices.copy()
    parties["filing_behaviour"] = None
    parties["gstin_status"] = "active"
    parties["cancelled_from"] = pd.NaT
    if manifest is None:
        return parties, invoices
    behaviour = manifest["filing_behaviour"]
    parties["filing_behaviour"] = parties["party_id"].map(behaviour).astype("object").where(parties["party_id"].isin(behaviour), None)
    for item in manifest["cancelled_suppliers"]:
        row = parties["party_id"] == item["party_id"]
        parties.loc[row, "gstin_status"] = "cancelled"
        parties.loc[row, "cancelled_from"] = pd.Timestamp(item["cancelled_from"])
    for ring in manifest["pan_rings"]:
        row = parties["party_id"] == ring["customer_party_id"]
        parties.loc[row, ["gstin", "pan"]] = [ring["new_gstin"], ring["new_pan"]]
        on_invoice = (invoices["party_id"] == ring["customer_party_id"]) & (invoices["party_gstin"] == ring["old_gstin"])
        invoices.loc[on_invoice, "party_gstin"] = ring["new_gstin"]
    return parties, invoices


def load_dataset(
    path: str | Path | None = None,
    derived_dir: str | Path | None = None,
    expected_sha256: str | None = config.DATASET_SHA256,
) -> Dataset:
    """Load the workbook and, when present, the augmentation files next to it.

    Pass expected_sha256=None only for fixture workbooks.
    """
    path = Path(path) if path is not None else config.DATASET_PATH
    derived_dir = Path(derived_dir) if derived_dir is not None else config.DERIVED_DIR
    sha = file_sha256(path)
    if expected_sha256 is not None and sha != expected_sha256:
        raise DatasetError(f"{path}: SHA-256 {sha} does not match the expected {expected_sha256}")

    manifest = None
    manifest_path = derived_dir / "augment_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["source_sha256"] != sha:
            raise DatasetError(f"{manifest_path} was generated from a different workbook; run augment again")

    raw = pd.read_excel(path, sheet_name=None)
    missing = [s for s in SHEETS if s not in raw]
    extra = [s for s in raw if s not in SHEETS]
    if missing or extra:
        raise DatasetError(f"{path}: missing sheets {missing}, unknown sheets {extra}")
    frames = {name: typed_frame(raw[name], contract, name) for name, contract in SHEETS.items()}

    labels = frames["labels"]
    labels["source"] = "workbook"
    gstr2b = None
    if manifest is not None:
        gstr2b = read_gstr2b(derived_dir / "gstr2b.csv")
        labels = pd.concat([labels, read_augment_labels(derived_dir / "augment_labels.csv")], ignore_index=True)
    parties, invoices = apply_manifest(frames["party_master"], frames["invoices"], manifest)

    return Dataset(
        invoices=invoices,
        bank=frames["bank_transactions"],
        ledger=frames["accounting_ledger"],
        tax_rates=frames["tax_rates"],
        parties=parties,
        filings=frames["tax_filings"],
        answer_key=frames["answer_key"],
        labels=labels,
        links=frames["links"],
        gstr2b=gstr2b,
        manifest=manifest,
        sha256=sha,
    )
