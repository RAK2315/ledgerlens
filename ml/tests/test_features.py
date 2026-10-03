import math

import numpy as np
import pandas as pd
import pytest

from ledgerlens_ml import config
from ledgerlens_ml.candidates import booking_candidates, payment_candidates
from ledgerlens_ml.features import booking_features, payment_features
from ledgerlens_ml.parties import resolve_bank

INVOICES = pd.DataFrame({
    "invoice_id": ["INV-2526-02759", "VEN042-0001"],
    "doc_type": ["INVOICE", "INVOICE"],
    "invoice_type": ["SALES", "PURCHASE"],
    "invoice_date": pd.to_datetime(["2025-06-10", "2025-06-28"]),
    "party_id": ["CUS-001", "VEN-042"],
    "taxable_value_paise": [100_000_00, 50_000_00],
    "total_tax_paise": [18_000_00, 9_000_00],
    "invoice_total_paise": [118_000_00, 59_000_00],
})

LEDGER = pd.DataFrame({
    "entry_id": ["JE-1", "JE-2", "JE-3"],
    "posting_date": pd.to_datetime(["2025-06-12", "2025-07-02", "2025-06-28"]),
    "invoice_ref": ["INV-2425-02759", None, "VEN042-0001"],
    "taxable_amount_paise": pd.array([100_000_00, 90_000_00, 50_000_00], dtype="Int64"),
    "total_tax_paise": pd.array([18_000_00, 16_200_00, 9_000_00], dtype="Int64"),
    "total_amount_paise": [118_000_00, 106_200_00, 59_000_00],
})

BANK = pd.DataFrame({
    "txn_id": ["TXN-1", "TXN-2", "TXN-3"],
    "txn_date": pd.to_datetime(["2025-07-05", "2025-07-20", "2025-07-01"]),
    "amount_paise": [118_000_00, 118_001_40, 59_000_00],
    "narration": ["NEFT/U1/ACME LTD/inv252602759", "NEFT/U2/ACME LTD", "NEFT/U3/EVERGREEN INFRA/0001"],
    "resolved_party_id": ["CUS-001", "CUS-001", "VEN-042"],
    "resolve_score": [100.0, 92.0, 100.0],
    "resolve_method": ["invoice_ref", "name", "account"],
})


def row(frame, invoice_id, right_id):
    return frame[(frame["invoice_id"] == invoice_id) & (frame["right_id"] == right_id)].iloc[0]


@pytest.fixture(scope="module")
def booking():
    pairs = pd.DataFrame({"invoice_id": ["INV-2526-02759", "INV-2526-02759", "VEN042-0001"], "right_id": ["JE-1", "JE-2", "JE-3"]})
    return booking_features(pairs, INVOICES, LEDGER)


@pytest.fixture(scope="module")
def payment():
    pairs = pd.DataFrame({"invoice_id": ["INV-2526-02759", "INV-2526-02759", "VEN042-0001"], "right_id": ["TXN-1", "TXN-2", "TXN-3"]})
    return payment_features(pairs, INVOICES, BANK)


def test_column_order_equals_config(booking, payment):
    assert list(booking.columns) == ["invoice_id", "right_id", *config.MATCHER_FEATURES_A]
    assert list(payment.columns) == ["invoice_id", "right_id", *config.MATCHER_FEATURES_B]
    for frame in (booking, payment):
        assert all(frame[c].dtype == np.float64 for c in frame.columns[2:])


def test_booking_id_features(booking):
    wrong_year = row(booking, "INV-2526-02759", "JE-1")
    assert wrong_year["id_exact"] == 0
    assert wrong_year["id_norm_exact"] == 1
    assert wrong_year["id_serial_equal"] == 1
    assert wrong_year["id_ratio"] == 1.0
    assert 0.8 < wrong_year["id_dl_sim"] < 1.0
    assert wrong_year["id_missing"] == 0

    no_ref = row(booking, "INV-2526-02759", "JE-2")
    assert (no_ref["id_exact"], no_ref["id_norm_exact"], no_ref["id_serial_equal"], no_ref["id_missing"]) == (0, 0, 0, 1)
    assert math.isnan(no_ref["id_ratio"]) and math.isnan(no_ref["id_dl_sim"])

    exact = row(booking, "VEN042-0001", "JE-3")
    assert (exact["id_exact"], exact["id_norm_exact"], exact["id_dl_sim"]) == (1, 1, 1.0)


def test_booking_amount_and_date_features(booking):
    close = row(booking, "INV-2526-02759", "JE-1")
    assert close["amt_rel_diff"] == 0
    assert close["amt_within_1"] == 1
    assert close["amt_ratio"] == 1.0
    assert close["amt_log_left"] == pytest.approx(math.log10(118_000))
    assert close["tax_rel_diff"] == 0 and close["taxable_rel_diff"] == 0
    assert (close["date_diff_days"], close["date_abs_diff"], close["same_period"]) == (2, 2, 1)
    assert (close["amt_rank"], close["date_rank"], close["n_candidates"]) == (1, 1, 2)
    assert close["party_score"] == 1.0

    far = row(booking, "INV-2526-02759", "JE-2")
    assert far["amt_rel_diff"] == pytest.approx(11_800 / 118_000)
    assert far["amt_within_1"] == 0
    assert far["amt_ratio"] == pytest.approx(0.9)
    assert far["taxable_rel_diff"] == pytest.approx(0.1)
    assert (far["date_diff_days"], far["same_period"]) == (22, 0)
    assert (far["amt_rank"], far["date_rank"]) == (2, 2)


def test_payment_features(payment):
    quoted = row(payment, "INV-2526-02759", "TXN-1")
    assert quoted["id_exact"] == 0
    assert quoted["id_norm_exact"] == 1
    assert quoted["id_serial_equal"] == 1
    assert quoted["id_missing"] == 0
    assert quoted["date_diff_days"] == 25
    assert (quoted["party_score"], quoted["party_method_ref"]) == (1.0, 1)
    assert (quoted["amt_rank"], quoted["n_candidates"]) == (1, 2)

    bare = row(payment, "INV-2526-02759", "TXN-2")
    assert bare["id_missing"] == 1 and math.isnan(bare["id_ratio"])
    assert bare["amt_within_1"] == 0
    assert bare["amt_rel_diff"] == pytest.approx(140 / 118_001_40)
    assert (bare["party_score"], bare["party_method_ref"]) == (0.92, 0)

    serial_only = row(payment, "VEN042-0001", "TXN-3")
    assert (serial_only["id_exact"], serial_only["id_norm_exact"], serial_only["id_serial_equal"]) == (0, 0, 1)
    assert serial_only["date_diff_days"] == 3


def test_credit_note_amounts_compare_by_size():
    invoices = INVOICES.assign(invoice_total_paise=[-118_000_00, 59_000_00], total_tax_paise=[-18_000_00, 9_000_00], taxable_value_paise=[-100_000_00, 50_000_00])
    ledger = LEDGER.assign(taxable_amount_paise=pd.array([-100_000_00, 90_000_00, 50_000_00], dtype="Int64"), total_tax_paise=pd.array([-18_000_00, 16_200_00, 9_000_00], dtype="Int64"))
    got = booking_features(pd.DataFrame({"invoice_id": ["INV-2526-02759"], "right_id": ["JE-1"]}), invoices, ledger).iloc[0]
    assert (got["amt_rel_diff"], got["amt_ratio"], got["tax_rel_diff"]) == (0, 1.0, 0)


def test_feature_frames_on_real_candidates_have_nan_only_in_id_similarity(mini):
    bank = resolve_bank(mini.bank, mini.parties, mini.invoices)
    frames = [
        booking_features(booking_candidates(mini.invoices, mini.ledger), mini.invoices, mini.ledger),
        payment_features(payment_candidates(mini.invoices, bank), mini.invoices, bank),
    ]
    for frame in frames:
        assert len(frame) > 500
        nan_columns = set(frame.columns[frame.isna().any()])
        assert nan_columns <= {"id_ratio", "id_dl_sim"}
        assert np.isfinite(frame.drop(columns=["invoice_id", "right_id", "id_ratio", "id_dl_sim"]).to_numpy(dtype=float)).all()
        assert frame["amt_rel_diff"].between(0, 1).all()
        assert (frame["amt_rank"] >= 1).all() and (frame["amt_rank"] <= frame["n_candidates"]).all()
