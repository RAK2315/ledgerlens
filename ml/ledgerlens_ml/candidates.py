"""Candidate pair generation (blocking) for each matcher (ML_BUILD.md 5.1). Frames in, frames out."""
from __future__ import annotations

from typing import Literal

import pandas as pd

from . import config
from .normalise import narration_id_tokens, normalise_invoice_id

PAYMENT_DIRECTION = {"PURCHASE": "DEBIT", "SALES": "CREDIT"}


def _in_window(pairs: pd.DataFrame, right_date: str, window: tuple[int, int]) -> pd.DataFrame:
    days = (pairs[right_date] - pairs["invoice_date"]).dt.days
    return pairs[days.between(*window)]


def _amount_rank(pairs: pd.DataFrame, right_amount: str) -> pd.Series:
    diff = (pairs["invoice_total_paise"].abs() - pairs[right_amount].abs()).abs()
    order = pairs.assign(_diff=diff).sort_values(["invoice_id", "_diff", "right_id"])
    return order.groupby("invoice_id").cumcount().reindex(pairs.index)


def booking_candidates(invoices: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    """Ledger entries of the matching voucher type and party, posted near the invoice date."""
    left = invoices[["invoice_id", "doc_type", "invoice_type", "invoice_date", "party_id", "invoice_total_paise"]].copy()
    left["voucher_type"] = left["invoice_type"].where(left["doc_type"] == "INVOICE", "CREDIT_NOTE")
    right = ledger[["entry_id", "voucher_type", "party_id", "posting_date", "total_amount_paise"]].rename(columns={"entry_id": "right_id"})
    pairs = left.merge(right.dropna(subset=["party_id"]), on=["voucher_type", "party_id"])
    pairs = _in_window(pairs, "posting_date", config.BOOKING_WINDOW)
    pairs = pairs[_amount_rank(pairs, "total_amount_paise") < config.CANDIDATE_CAP]
    return pairs[["invoice_id", "right_id"]].sort_values(["invoice_id", "right_id"]).reset_index(drop=True)


def payment_candidates(invoices: pd.DataFrame, bank: pd.DataFrame) -> pd.DataFrame:
    """Bank transactions in the paying direction from the same resolved party, or quoting the invoice ID.

    bank must carry resolved_party_id (parties.resolve_bank).
    """
    left = invoices.loc[invoices["doc_type"] == "INVOICE", ["invoice_id", "invoice_type", "invoice_date", "party_id", "invoice_total_paise"]].copy()
    left["direction"] = left["invoice_type"].map(PAYMENT_DIRECTION)
    left["id_norm"] = left["invoice_id"].map(normalise_invoice_id)
    right = bank[["txn_id", "direction", "txn_date", "amount_paise", "resolved_party_id", "narration"]].rename(columns={"txn_id": "right_id"})

    by_party = left.merge(right.dropna(subset=["resolved_party_id"]), left_on=["direction", "party_id"], right_on=["direction", "resolved_party_id"])
    refs = right.assign(id_norm=right["narration"].map(lambda n: sorted({normalise_invoice_id(t) for t in narration_id_tokens(n)}))).explode("id_norm")
    by_ref = left.merge(refs.dropna(subset=["id_norm"]), on=["direction", "id_norm"])
    by_ref["has_ref"] = True
    pairs = pd.concat([by_ref, by_party.assign(has_ref=False)], ignore_index=True).drop_duplicates(["invoice_id", "right_id"])
    pairs = _in_window(pairs, "txn_date", config.PAYMENT_WINDOW)
    pairs = pairs[(_amount_rank(pairs, "amount_paise") < config.CANDIDATE_CAP) | pairs["has_ref"]]
    return pairs[["invoice_id", "right_id"]].sort_values(["invoice_id", "right_id"]).reset_index(drop=True)


def true_pairs(links: pd.DataFrame, kind: Literal["booking", "payment"]) -> pd.DataFrame:
    """Ground truth pairs from the links sheet, as invoice_id and right_id."""
    column = "booking_entry_id" if kind == "booking" else "txn_id"
    pairs = links[["invoice_id", column]].dropna().rename(columns={column: "right_id"})
    return pairs.drop_duplicates().reset_index(drop=True)


def candidate_recall(candidates: pd.DataFrame, truth: pd.DataFrame) -> float:
    """Share of true pairs that survived candidate generation."""
    if truth.empty:
        return 1.0
    found = truth.merge(candidates, on=["invoice_id", "right_id"], how="left", indicator=True)
    return float((found["_merge"] == "both").mean())
