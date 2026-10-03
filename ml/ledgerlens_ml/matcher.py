"""Train, calibrate, save, load and score the booking and payment matchers (ML_BUILD.md 5)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel
from scipy.optimize import linear_sum_assignment
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

from . import config
from .candidates import booking_candidates, payment_candidates, true_pairs
from .data import Dataset
from .features import booking_features, invoice_split, payment_features, train_aggregates
from .parties import resolve_bank

Kind = Literal["booking", "payment"]
FEATURES = {"booking": list(config.MATCHER_FEATURES_A), "payment": list(config.MATCHER_FEATURES_B)}
BASELINE = "baseline"
AUTO_THRESHOLD_STEPS = (config.BAND_AUTO, 0.95, 0.98)
MAX_FALSE_AUTO_RATE = 0.01
MIN_F1_GAIN_OVER_BASELINE = 0.01
BENIGN_TRAP_LABELS = ("PARTIAL_PAYMENT", "BUNDLED_PAYMENT", "ROUNDING_NOISE")
TARGETS = {
    "booking": {"pair_f1": 0.97, "invoice_accuracy": 0.98, "id_mismatch_recall": 0.90, "benign_matched": 0.95, "false_auto_rate": 0.01},
    "payment": {"pair_f1": 0.95, "invoice_accuracy": 0.95, "id_mismatch_recall": 0.85, "benign_matched": 0.95, "false_auto_rate": 0.01},
}


class ModelNotTrainedError(Exception):
    """No artifact on disk for this matcher."""


class MatchResult(BaseModel):
    kind: Literal["booking", "payment", "gstr2b"]
    invoice_id: str
    right_id: str | None
    confidence: float
    band: Literal["auto", "review", "unmatched"]
    reasons: list[str]
    features: dict[str, float]


def pair_frame(kind: Kind, ds: Dataset, invoices: pd.DataFrame | None = None) -> pd.DataFrame:
    """Candidates and features for the given invoices (all of them by default)."""
    invoices = ds.invoices if invoices is None else invoices
    if kind == "booking":
        return booking_features(booking_candidates(invoices, ds.ledger), invoices, ds.ledger)
    bank = resolve_bank(ds.bank, ds.parties, ds.invoices)
    return payment_features(payment_candidates(invoices, bank), invoices, bank)


def baseline_score(features: pd.DataFrame) -> np.ndarray:
    """The rule score every model must beat; also the shipped matcher when the model does not."""
    id_sim = features["id_dl_sim"].fillna(0.0).to_numpy()
    amount = 1 - np.minimum(features["amt_rel_diff"].to_numpy() * 10, 1)
    date = 1 - np.minimum(features["date_abs_diff"].to_numpy() / 60, 1)
    return 0.45 * id_sim + 0.30 * amount + 0.15 * date + 0.10 * features["party_score"].to_numpy()


def score_features(artifact: dict, features: pd.DataFrame) -> np.ndarray:
    """Confidence for each feature row. Refuses an artifact trained on a different feature list."""
    expected = FEATURES[artifact["kind"]]
    if list(artifact["features"]) != expected:
        raise ValueError(f"matcher_{artifact['kind']} was trained on a different feature list; run train --model {artifact['kind']} again")
    if artifact["model"] == BASELINE:
        return np.clip(baseline_score(features), 0.0, 1.0)
    return artifact["model"].predict_proba(features[expected])[:, 1]


def band_of(confidence: float, thresholds: dict[str, float]) -> str:
    if confidence >= thresholds["auto"]:
        return "auto"
    return "review" if confidence >= thresholds["review"] else "unmatched"


def assign(scored: pd.DataFrame, floor: float = config.ASSIGNMENT_FLOOR) -> pd.DataFrame:
    """One-to-one assignment that maximises total confidence. Pairs below the floor are never used."""
    usable = scored[scored["confidence"] >= floor]
    if usable.empty:
        return usable[["invoice_id", "right_id", "confidence"]]
    left_codes, left_ids = pd.factorize(usable["invoice_id"])
    right_codes, right_ids = pd.factorize(usable["right_id"])
    n_left = len(left_ids)
    graph = coo_matrix((np.ones(len(usable)), (left_codes, right_codes + n_left)), shape=(n_left + len(right_ids),) * 2)
    _, component = connected_components(graph, directed=False)
    confidence = usable["confidence"].to_numpy()
    keep: list[int] = []
    for rows in pd.Series(np.arange(len(usable))).groupby(component[left_codes]).indices.values():
        lefts, li = np.unique(left_codes[rows], return_inverse=True)
        rights, ri = np.unique(right_codes[rows], return_inverse=True)
        cost = np.full((len(lefts), len(rights)), 10.0)
        cost[li, ri] = 1 - confidence[rows]
        position = np.full((len(lefts), len(rights)), -1)
        position[li, ri] = rows
        for a, b in zip(*linear_sum_assignment(cost)):
            if position[a, b] >= 0:
                keep.append(int(position[a, b]))
    return usable.iloc[sorted(keep)][["invoice_id", "right_id", "confidence"]].reset_index(drop=True)


def _rupees(amount: float) -> str:
    """Rs with Indian digit grouping and two decimals."""
    whole, paise = divmod(int(round(abs(amount) * 100)), 100)
    digits = str(whole)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return "Rs " + ",".join(groups + [tail]) + f".{paise:02d}"


def reasons_for(kind: Kind, f: dict[str, float]) -> list[str]:
    """Up to three plain sentences from feature values: invoice number, amount, date."""
    other = "ledger entry" if kind == "booking" else "bank narration"
    if f["id_missing"]:
        number = f"No invoice number in the {other}"
    elif f["id_exact"]:
        number = "Invoice number matches exactly" if kind == "booking" else "Bank narration quotes the invoice number"
    elif f["id_norm_exact"]:
        number = "Invoice number matches after removing prefix and year"
    elif f["id_serial_equal"]:
        number = "Invoice serial number matches"
    elif f["id_dl_sim"] >= 0.85:
        number = "Invoice number differs by one or two characters"
    else:
        number = f"Invoice number in the {other} is different"
    if f["amt_within_1"]:
        amount = "Amount matches"
    else:
        amount = f"Amount differs by {_rupees(abs(f['amt_ratio'] - 1) * 10 ** f['amt_log_left'])}"
    days = int(round(f["date_diff_days"]))
    verb = "Booked" if kind == "booking" else "Paid"
    if days == 0:
        date = f"{verb} on the invoice date"
    else:
        date = f"{verb} {abs(days)} day{'' if abs(days) == 1 else 's'} {'after' if days > 0 else 'before'} the invoice date"
    return [number, amount, date]


def _hard_case_entities(labels: pd.DataFrame) -> dict[str, set[str]]:
    hard = labels[labels["issue_type"].isin(config.HARD_CASE_LABELS)]
    return {issue: set(group["entity_id"]) | set(group["related_entity_id"].dropna()) for issue, group in hard.groupby("issue_type")}


def _labelled_frame(kind: Kind, ds: Dataset) -> pd.DataFrame:
    """Feature frame with y, split and the hard-case sample weight."""
    frame = pair_frame(kind, ds)
    truth = true_pairs(ds.links, kind).assign(y=1)
    frame = frame.merge(truth, on=["invoice_id", "right_id"], how="left")
    frame["y"] = frame["y"].fillna(0).astype(int)
    frame["split"] = frame["invoice_id"].map(dict(zip(ds.invoices["invoice_id"], invoice_split(ds.invoices))))
    hard = set().union(*_hard_case_entities(ds.labels).values()) if len(ds.labels) else set()
    is_hard = frame["invoice_id"].isin(hard) | frame["right_id"].isin(hard)
    frame["weight"] = np.where((frame["y"] == 1) & is_hard, 3.0, 1.0)
    return frame


def _fit(train: pd.DataFrame, val: pd.DataFrame, names: list[str]) -> tuple[HistGradientBoostingClassifier, int]:
    """Grow trees 20 at a time, keep the count with the best average precision on the validation month."""
    params = dict(learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1.0,
                  early_stopping=False, class_weight="balanced", random_state=config.SEED)
    model = HistGradientBoostingClassifier(max_iter=20, warm_start=True, **params)
    best_iter, best_ap, stale = 20, -1.0, 0
    for n_iter in range(20, 401, 20):
        model.set_params(max_iter=n_iter)
        model.fit(train[names], train["y"], sample_weight=train["weight"])
        ap = average_precision_score(val["y"], model.predict_proba(val[names])[:, 1])
        if ap > best_ap + 1e-6:
            best_iter, best_ap, stale = n_iter, ap, 0
        else:
            stale += 1
            if stale == 3:
                break
    final = HistGradientBoostingClassifier(max_iter=best_iter, **params)
    final.fit(train[names], train["y"], sample_weight=train["weight"])
    return final, best_iter


def _auto_threshold(confidence: np.ndarray, y: np.ndarray) -> float:
    """The lowest auto threshold with at most 1 percent false auto-matches on validation."""
    for threshold in AUTO_THRESHOLD_STEPS:
        auto = confidence >= threshold
        if auto.sum() == 0 or (1 - y[auto]).mean() <= MAX_FALSE_AUTO_RATE:
            return threshold
    return AUTO_THRESHOLD_STEPS[-1]


def _metrics(frame: pd.DataFrame, confidence: np.ndarray, thresholds: dict[str, float], labels: pd.DataFrame) -> dict:
    """Section 5.5 metrics for one split."""
    scored = frame[["invoice_id", "right_id", "y"]].assign(confidence=confidence)
    y = scored["y"].to_numpy()
    auto = confidence >= thresholds["auto"]
    precision, recall, f1, _ = precision_recall_fscore_support(y, auto, average="binary", zero_division=0)
    pair = {
        "pairs": int(len(scored)), "positives": int(y.sum()), "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "average_precision": float(average_precision_score(y, confidence)) if 0 < y.sum() < len(y) else None,
        "false_auto_rate": float((1 - y[auto]).mean()) if auto.sum() else 0.0,
    }

    assigned = assign(scored)
    assigned = assigned[assigned["confidence"] >= thresholds["review"]]
    truth = scored[scored["y"] == 1].groupby("invoice_id")["right_id"].agg(set)
    got = assigned.set_index("invoice_id")["right_id"]
    correct = sum(got.get(invoice_id) in partners for invoice_id, partners in truth.items())
    without_truth = set(scored["invoice_id"]) - set(truth.index)
    invoice_level = {
        "invoices_with_a_true_partner": int(len(truth)), "accuracy": correct / len(truth) if len(truth) else None,
        "invoices_without_a_true_partner": len(without_truth),
        "left_unmatched": 1 - len(without_truth & set(got.index)) / len(without_truth) if without_truth else None,
    }

    positives = scored[scored["y"] == 1]
    hard_cases = {}
    for issue, entities in _hard_case_entities(labels).items():
        rows = positives[positives["invoice_id"].isin(entities) | positives["right_id"].isin(entities)]
        if len(rows):
            hard_cases[issue] = {"pairs": int(len(rows)), "recall_auto": float((rows["confidence"] >= thresholds["auto"]).mean()),
                                 "recall_review": float((rows["confidence"] >= thresholds["review"]).mean())}
    benign = {}
    for issue in BENIGN_TRAP_LABELS:
        entities = set(labels.loc[labels["issue_type"] == issue, "entity_id"])
        rows = positives[positives["invoice_id"].isin(entities) | positives["right_id"].isin(entities)]
        if len(rows):
            benign[issue] = {"pairs": int(len(rows)), "matched": float((rows["confidence"] >= thresholds["review"]).mean())}
    return {"pair": pair, "invoice_level": invoice_level, "hard_cases": hard_cases, "benign_traps": benign}


def _targets_table(kind: Kind, test: dict) -> list[dict]:
    target = TARGETS[kind]
    id_mismatch = test["hard_cases"].get("INVOICE_ID_MISMATCH", {}).get("recall_review")
    benign = [v["matched"] for v in test["benign_traps"].values()]
    actual = {
        "pair_f1": test["pair"]["f1"], "invoice_accuracy": test["invoice_level"]["accuracy"], "id_mismatch_recall": id_mismatch,
        "benign_matched": min(benign) if benign else None, "false_auto_rate": test["pair"]["false_auto_rate"],
    }
    rows = []
    for name, goal in target.items():
        value = actual[name]
        met = None if value is None else (value <= goal if name == "false_auto_rate" else value >= goal)
        rows.append({"metric": name, "target": goal, "actual": value, "met": met})
    return rows


def train_matcher(kind: Kind, ds: Dataset) -> tuple[dict, dict]:
    """Fit, calibrate and evaluate one matcher. Returns the artifact and its card."""
    names = FEATURES[kind]
    frame = _labelled_frame(kind, ds)
    train, val, test = (frame[frame["split"] == s] for s in ("train", "validation", "test"))
    model, best_iter = _fit(train, val, names)
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="isotonic").fit(val[names], val["y"])

    val_conf = calibrated.predict_proba(val[names])[:, 1]
    thresholds = {"auto": _auto_threshold(val_conf, val["y"].to_numpy()), "review": config.BAND_REVIEW}
    baseline_thresholds = {"auto": config.BAND_AUTO, "review": config.BAND_REVIEW}
    model_test = _metrics(test, calibrated.predict_proba(test[names])[:, 1], thresholds, ds.labels)
    baseline_test = _metrics(test, np.clip(baseline_score(test), 0, 1), baseline_thresholds, ds.labels)
    ship_model = model_test["pair"]["f1"] >= baseline_test["pair"]["f1"] + MIN_F1_GAIN_OVER_BASELINE

    importance = permutation_importance(model, val[names], val["y"], scoring="average_precision", n_repeats=5, random_state=config.SEED)
    artifact = {
        "kind": kind,
        "model": calibrated if ship_model else BASELINE,
        "features": names,
        "thresholds": thresholds if ship_model else baseline_thresholds,
        "frozen_aggregates": train_aggregates(ds.invoices),
        "model_version": config.MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_sha256": ds.sha256,
    }
    shipped_test = model_test if ship_model else baseline_test
    card = {
        **{k: artifact[k] for k in ("kind", "features", "thresholds", "model_version", "trained_at", "data_sha256")},
        "shipped": "model" if ship_model else "baseline",
        "best_iteration": best_iter,
        "rows": {"train": int(len(train)), "validation": int(len(val)), "test": int(len(test))},
        "targets": _targets_table(kind, shipped_test),
        "test": {**shipped_test, "baseline": baseline_test["pair"], "model": model_test["pair"],
                 "f1_gain_over_baseline": model_test["pair"]["f1"] - baseline_test["pair"]["f1"]},
        "validation": _metrics(val, val_conf, thresholds, ds.labels),
        "feature_importance": dict(sorted(zip(names, map(float, importance.importances_mean)), key=lambda kv: -kv[1])),
    }
    return artifact, card


def save_artifact(artifact: dict, card: dict, out_dir: str | Path | None = None) -> Path:
    out_dir = Path(out_dir) if out_dir is not None else config.ARTIFACTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, out_dir / f"matcher_{artifact['kind']}.joblib")
    (out_dir / f"matcher_{artifact['kind']}.card.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    return out_dir


def load_artifact(kind: Kind, artifacts_dir: str | Path | None = None) -> dict:
    path = (Path(artifacts_dir) if artifacts_dir is not None else config.ARTIFACTS_DIR) / f"matcher_{kind}.joblib"
    if not path.exists():
        raise ModelNotTrainedError(f"{path.name} not found; run python -m ledgerlens_ml train --model {kind}")
    return joblib.load(path)


def _scope(invoices: pd.DataFrame, period: str | None) -> pd.DataFrame:
    """Invoices that can compete for the same right-side records as the period's invoices."""
    if period is None:
        return invoices
    start = pd.Period(period, freq="M").start_time
    end = pd.Period(period, freq="M").end_time
    near = invoices["invoice_date"].between(start - pd.Timedelta(days=120), end + pd.Timedelta(days=60))
    return invoices[near]


def score_pairs(kind: Kind, ds: Dataset, period: str | None = None, artifacts_dir: str | Path | None = None) -> list[MatchResult]:
    """One MatchResult per invoice in the period: its assigned partner, Confidence, Band and reasons."""
    artifact = load_artifact(kind, artifacts_dir)
    invoices = ds.invoices if kind == "booking" else ds.invoices[ds.invoices["doc_type"] == "INVOICE"]
    frame = pair_frame(kind, ds, _scope(invoices, period))
    frame["confidence"] = score_features(artifact, frame)
    assigned = assign(frame).merge(frame, on=["invoice_id", "right_id", "confidence"], how="left").set_index("invoice_id")
    wanted = invoices if period is None else invoices[invoices["invoice_date"].dt.strftime("%Y-%m") == period]
    names = FEATURES[kind]
    results = []
    for invoice_id in wanted["invoice_id"]:
        if invoice_id not in assigned.index:
            results.append(MatchResult(kind=kind, invoice_id=invoice_id, right_id=None, confidence=0.0, band="unmatched", reasons=[], features={}))
            continue
        row = assigned.loc[invoice_id]
        confidence = float(row["confidence"])
        band = band_of(confidence, artifact["thresholds"])
        features = {name: float(row[name]) for name in names}
        results.append(MatchResult(kind=kind, invoice_id=invoice_id, right_id=row["right_id"] if band != "unmatched" else None,
                                   confidence=confidence, band=band, reasons=reasons_for(kind, features), features=features))
    return results
