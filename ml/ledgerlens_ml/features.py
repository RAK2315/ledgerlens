"""Pair features for the matchers and train-only aggregates (ML_BUILD.md 3.6, 5.2). Pure: frames in, frames out."""
from __future__ import annotations

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.distance import DamerauLevenshtein

from . import config
from .normalise import id_serial, narration_id_tokens, normalise_invoice_id

SPLIT_OF_MONTH = {
    **{m: "train" for m in config.TRAIN_MONTHS},
    **{m: "validation" for m in config.VALIDATION_MONTHS},
    **{m: "test" for m in config.TEST_MONTHS},
}


def invoice_split(invoices: pd.DataFrame) -> pd.Series:
    """train, validation or test for each invoice, by the month of its date. A pair takes its invoice's split."""
    return invoices["invoice_date"].dt.strftime("%Y-%m").map(SPLIT_OF_MONTH)


def train_aggregates(invoices: pd.DataFrame) -> dict:
    """Party and category medians from train months only, frozen into model artifacts."""
    train = invoices[(invoice_split(invoices) == "train") & (invoices["doc_type"] == "INVOICE")]
    by_party = train.groupby("party_id")["taxable_value_paise"]
    return {
        "party_median_taxable_paise": by_party.median().astype(float).to_dict(),
        "party_train_count": by_party.size().astype(int).to_dict(),
        "category_median_taxable_paise": train.groupby("category")["taxable_value_paise"].median().astype(float).to_dict(),
        "taxable_p95_paise": float(train["taxable_value_paise"].quantile(0.95)),
    }


def _rel_diff(left: pd.Series, right: pd.Series) -> pd.Series:
    left, right = left.astype(float).abs(), right.astype(float).abs()
    largest = np.maximum(left, right)
    return ((left - right).abs() / largest.where(largest > 0, 1.0)).fillna(1.0)


def _id_similarity(left_raw: str, left_norm: str, right_raws: list[str]) -> tuple[float, float]:
    """Best fuzz ratio on normalised IDs and best Damerau-Levenshtein similarity on raw IDs, both 0 to 1."""
    if not right_raws:
        return np.nan, np.nan
    left_upper = left_raw.upper()
    ratio = max(fuzz.ratio(left_norm, normalise_invoice_id(r)) for r in right_raws) / 100
    dl = max(DamerauLevenshtein.normalized_similarity(left_upper, r.upper()) for r in right_raws)
    return ratio, dl


def _shared_features(pairs: pd.DataFrame, right_ids: list[list[str]], right_amount: str, right_date: str) -> pd.DataFrame:
    """Features both matchers share. pairs holds the invoice columns and the right side's amount and date."""
    out = pd.DataFrame({"invoice_id": pairs["invoice_id"].to_numpy(), "right_id": pairs["right_id"].to_numpy()})
    left_raw = pairs["invoice_id"].tolist()
    left_norm = [normalise_invoice_id(x) for x in left_raw]
    left_serial = [id_serial(x) for x in left_raw]
    similarity = [_id_similarity(raw, norm, rights) for raw, norm, rights in zip(left_raw, left_norm, right_ids)]
    out["id_norm_exact"] = [float(any(normalise_invoice_id(r) == n for r in rights)) for n, rights in zip(left_norm, right_ids)]
    out["id_serial_equal"] = [float(any(id_serial(r) == s for r in rights)) for s, rights in zip(left_serial, right_ids)]
    out["id_ratio"] = [s[0] for s in similarity]
    out["id_dl_sim"] = [s[1] for s in similarity]
    out["id_missing"] = [float(not rights) for rights in right_ids]

    left_amount = pairs["invoice_total_paise"].astype(float).abs().to_numpy()
    right_amount_abs = pairs[right_amount].astype(float).abs().to_numpy()
    out["amt_rel_diff"] = _rel_diff(pairs["invoice_total_paise"], pairs[right_amount]).to_numpy()
    out["amt_within_1"] = (np.abs(left_amount - right_amount_abs) <= 100).astype(float)
    out["amt_ratio"] = right_amount_abs / np.where(left_amount > 0, left_amount, 1.0)
    out["amt_log_left"] = np.log10(np.maximum(left_amount, 1.0) / 100)
    days = (pairs[right_date] - pairs["invoice_date"]).dt.days.astype(float).to_numpy()
    out["date_diff_days"] = days
    out["date_abs_diff"] = np.abs(days)
    by_invoice = out.groupby("invoice_id")
    out["amt_rank"] = by_invoice["amt_rel_diff"].rank(method="min")
    out["date_rank"] = by_invoice["date_abs_diff"].rank(method="min")
    out["n_candidates"] = by_invoice["right_id"].transform("size").astype(float)
    return out


def booking_features(candidates: pd.DataFrame, invoices: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    """One row per invoice and ledger entry pair, columns in MATCHER_FEATURES_A order."""
    left = invoices[["invoice_id", "invoice_date", "taxable_value_paise", "total_tax_paise", "invoice_total_paise"]]
    right = ledger[["entry_id", "posting_date", "invoice_ref", "taxable_amount_paise", "total_tax_paise", "total_amount_paise"]]
    right = right.rename(columns={"entry_id": "right_id", "total_tax_paise": "right_tax_paise"})
    pairs = candidates.merge(left, on="invoice_id", how="left").merge(right, on="right_id", how="left")
    refs = [[ref] if isinstance(ref, str) else [] for ref in pairs["invoice_ref"]]
    out = _shared_features(pairs, refs, "total_amount_paise", "posting_date")
    out["id_exact"] = (pairs["invoice_id"] == pairs["invoice_ref"]).astype(float).to_numpy()
    out["tax_rel_diff"] = _rel_diff(pairs["total_tax_paise"], pairs["right_tax_paise"]).to_numpy()
    out["taxable_rel_diff"] = _rel_diff(pairs["taxable_value_paise"], pairs["taxable_amount_paise"]).to_numpy()
    out["same_period"] = (pairs["invoice_date"].dt.to_period("M") == pairs["posting_date"].dt.to_period("M")).astype(float).to_numpy()
    out["party_score"] = 1.0
    return out[["invoice_id", "right_id", *config.MATCHER_FEATURES_A]]


def payment_features(candidates: pd.DataFrame, invoices: pd.DataFrame, bank: pd.DataFrame) -> pd.DataFrame:
    """One row per invoice and bank transaction pair, columns in MATCHER_FEATURES_B order.

    bank must carry the resolver columns (parties.resolve_bank).
    """
    left = invoices[["invoice_id", "invoice_date", "party_id", "invoice_total_paise"]]
    right = bank[["txn_id", "txn_date", "amount_paise", "narration", "resolved_party_id", "resolve_score", "resolve_method"]]
    pairs = candidates.merge(left, on="invoice_id", how="left").merge(right.rename(columns={"txn_id": "right_id"}), on="right_id", how="left")
    tokens = {narration: narration_id_tokens(narration) for narration in pairs["narration"].unique()}
    out = _shared_features(pairs, [tokens[n] for n in pairs["narration"]], "amount_paise", "txn_date")
    out["id_exact"] = [float(i.upper() in n.upper()) for i, n in zip(pairs["invoice_id"], pairs["narration"])]
    same_party = (pairs["resolved_party_id"] == pairs["party_id"]).to_numpy()
    out["party_score"] = np.where(same_party, pairs["resolve_score"].to_numpy(dtype=float) / 100, 0.0)
    out["party_method_ref"] = (pairs["resolve_method"] == "invoice_ref").astype(float).to_numpy()
    return out[["invoice_id", "right_id", *config.MATCHER_FEATURES_B]]
