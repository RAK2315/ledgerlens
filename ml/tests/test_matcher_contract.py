import numpy as np
import pandas as pd
import pytest

from ledgerlens_ml import config, matcher
from ledgerlens_ml.matcher import (
    ModelNotTrainedError,
    assign,
    band_of,
    baseline_score,
    load_artifact,
    reasons_for,
    save_artifact,
    score_features,
    score_pairs,
    train_matcher,
)


@pytest.fixture(scope="module")
def trained(mini, tmp_path_factory):
    out = tmp_path_factory.mktemp("artifacts")
    results = {}
    for kind in ("booking", "payment"):
        artifact, card = train_matcher(kind, mini)
        save_artifact(artifact, card, out)
        results[kind] = (artifact, card)
    return out, results


def test_artifact_round_trips(trained):
    out, results = trained
    for kind, (artifact, card) in results.items():
        loaded = load_artifact(kind, out)
        assert set(loaded) == {"kind", "model", "features", "thresholds", "frozen_aggregates", "model_version", "trained_at", "data_sha256"}
        assert loaded["features"] == artifact["features"] == list(config.MATCHER_FEATURES_A if kind == "booking" else config.MATCHER_FEATURES_B)
        assert loaded["model_version"] == config.MODEL_VERSION
        assert (out / f"matcher_{kind}.card.json").exists()
        assert card["shipped"] in ("model", "baseline")
        assert {"pair", "invoice_level", "hard_cases", "benign_traps", "baseline"} <= set(card["test"])


def test_missing_artifact_names_the_fix(tmp_path):
    with pytest.raises(ModelNotTrainedError, match="train --model booking"):
        load_artifact("booking", tmp_path)


def test_inference_rejects_a_mismatched_feature_list(trained):
    out, _ = trained
    artifact = load_artifact("booking", out)
    frame = pd.DataFrame({name: [0.0] for name in artifact["features"]})
    assert len(score_features(artifact, frame)) == 1
    stale = {**artifact, "features": artifact["features"][:-1]}
    with pytest.raises(ValueError, match="feature list"):
        score_features(stale, frame)


def test_confidence_is_a_probability_and_band_follows_thresholds(mini, trained):
    out, _ = trained
    for kind in ("booking", "payment"):
        results = score_pairs(kind, mini, artifacts_dir=out)
        assert len(results) == len(mini.invoices) if kind == "booking" else len(results) == int((mini.invoices["doc_type"] == "INVOICE").sum())
        thresholds = load_artifact(kind, out)["thresholds"]
        for r in results:
            assert r.kind == kind
            assert 0.0 <= r.confidence <= 1.0
            assert r.band == band_of(r.confidence, thresholds)
            assert len(r.reasons) <= 3
            assert (r.right_id is None) == (r.band == "unmatched")
        matched = [r for r in results if r.right_id]
        assert len(matched) > 0.6 * len(results)
        assert len({r.right_id for r in matched}) == len(matched)


def test_score_pairs_for_one_period_returns_that_period_only(mini, trained):
    out, _ = trained
    results = score_pairs("booking", mini, period="2025-09", artifacts_dir=out)
    in_period = mini.invoices[mini.invoices["invoice_date"].dt.strftime("%Y-%m") == "2025-09"]
    assert sorted(r.invoice_id for r in results) == sorted(in_period["invoice_id"])


def test_band_of():
    thresholds = {"auto": 0.90, "review": 0.70}
    assert [band_of(c, thresholds) for c in (0.95, 0.90, 0.89, 0.70, 0.69, 0.0)] == ["auto", "auto", "review", "review", "unmatched", "unmatched"]


def test_baseline_score_formula():
    frame = pd.DataFrame({
        "id_dl_sim": [1.0, 0.5, np.nan], "amt_rel_diff": [0.0, 0.05, 0.2],
        "date_abs_diff": [0.0, 30.0, 90.0], "party_score": [1.0, 1.0, 0.0],
    })
    got = baseline_score(frame)
    assert got[0] == pytest.approx(1.0)
    assert got[1] == pytest.approx(0.45 * 0.5 + 0.30 * 0.5 + 0.15 * 0.5 + 0.10)
    assert got[2] == pytest.approx(0.0)


def test_assign_is_one_to_one_and_never_forces_weak_pairs():
    scored = pd.DataFrame({
        "invoice_id": ["A", "A", "B", "B", "C"],
        "right_id": ["x", "y", "x", "y", "z"],
        "confidence": [0.95, 0.80, 0.90, 0.20, 0.10],
    })
    got = assign(scored).set_index("invoice_id")["right_id"].to_dict()
    # B can only take x, so A gives it up for y: 0.80 + 0.90 beats 0.95 alone.
    assert got == {"A": "y", "B": "x"}


def test_reasons_are_plain_sentences():
    booking = reasons_for("booking", {"id_exact": 0.0, "id_norm_exact": 1.0, "id_serial_equal": 1.0, "id_dl_sim": 0.86, "id_missing": 0.0,
                                      "amt_within_1": 0.0, "amt_ratio": 1.0001, "amt_log_left": 4.0, "date_diff_days": 3.0})
    assert booking == ["Invoice number matches after removing prefix and year", "Amount differs by Rs 1.00", "Booked 3 days after the invoice date"]
    payment = reasons_for("payment", {"id_exact": 1.0, "id_norm_exact": 1.0, "id_serial_equal": 1.0, "id_dl_sim": 1.0, "id_missing": 0.0,
                                      "amt_within_1": 1.0, "amt_ratio": 1.0, "amt_log_left": 5.0, "date_diff_days": -2.0})
    assert payment == ["Bank narration quotes the invoice number", "Amount matches", "Paid 2 days before the invoice date"]
    assert matcher.reasons_for("payment", {"id_missing": 1.0, "id_exact": 0.0, "id_norm_exact": 0.0, "id_serial_equal": 0.0, "id_dl_sim": float("nan"),
                                           "amt_within_1": 1.0, "amt_ratio": 1.0, "amt_log_left": 5.0, "date_diff_days": 0.0})[0] == "No invoice number in the bank narration"
