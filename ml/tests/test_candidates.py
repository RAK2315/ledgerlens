import pandas as pd
import pytest

from ledgerlens_ml import config
from ledgerlens_ml.candidates import booking_candidates, candidate_recall, payment_candidates, true_pairs
from ledgerlens_ml.parties import resolve_bank


@pytest.fixture(scope="module")
def bank(mini):
    return resolve_bank(mini.bank, mini.parties, mini.invoices)


@pytest.fixture(scope="module")
def booking(mini):
    return booking_candidates(mini.invoices, mini.ledger)


@pytest.fixture(scope="module")
def payment(mini, bank):
    return payment_candidates(mini.invoices, bank)


def test_candidate_frames_have_two_id_columns_and_no_repeats(booking, payment):
    for frame in (booking, payment):
        assert list(frame.columns) == ["invoice_id", "right_id"]
        assert not frame.duplicated().any()
        assert len(frame) > 0


def test_booking_recall_gate(mini, booking):
    truth = true_pairs(mini.links, "booking")
    assert len(truth) > 250
    assert candidate_recall(booking, truth) >= config.CANDIDATE_RECALL_GATE


def test_payment_recall_gate(mini, payment):
    truth = true_pairs(mini.links, "payment")
    assert len(truth) > 250
    assert candidate_recall(payment, truth) >= config.CANDIDATE_RECALL_GATE


def test_booking_candidates_respect_type_party_window_and_cap(mini, booking):
    pairs = booking.merge(mini.invoices, on="invoice_id").merge(mini.ledger, left_on="right_id", right_on="entry_id", suffixes=("", "_led"))
    expected_voucher = pairs["invoice_type"].where(pairs["doc_type"] == "INVOICE", "CREDIT_NOTE")
    assert (pairs["voucher_type"] == expected_voucher).all()
    assert (pairs["party_id"] == pairs["party_id_led"]).all()
    days = (pairs["posting_date"] - pairs["invoice_date"]).dt.days
    assert days.between(*config.BOOKING_WINDOW).all()
    assert booking.groupby("invoice_id").size().max() <= config.CANDIDATE_CAP


def test_payment_candidates_never_cross_direction(mini, bank, payment):
    pairs = payment.merge(mini.invoices, on="invoice_id").merge(bank, left_on="right_id", right_on="txn_id")
    assert set(zip(pairs["invoice_type"], pairs["direction"])) <= {("PURCHASE", "DEBIT"), ("SALES", "CREDIT")}
    assert (pairs["doc_type"] == "INVOICE").all()
    days = (pairs["txn_date"] - pairs["invoice_date"]).dt.days
    assert days.between(*config.PAYMENT_WINDOW).all()


def test_cap_keeps_the_closest_amounts():
    invoices = pd.DataFrame({
        "invoice_id": ["VEN001-0001"], "doc_type": ["INVOICE"], "invoice_type": ["PURCHASE"],
        "invoice_date": [pd.Timestamp("2025-06-01")], "party_id": ["VEN-001"], "invoice_total_paise": [100_000],
    })
    n = config.CANDIDATE_CAP + 5
    ledger = pd.DataFrame({
        "entry_id": [f"JE-{i:03d}" for i in range(n)], "voucher_type": ["PURCHASE"] * n, "party_id": ["VEN-001"] * n,
        "posting_date": [pd.Timestamp("2025-06-02")] * n, "total_amount_paise": [100_000 + 1_000 * i for i in range(n)],
    })
    got = booking_candidates(invoices, ledger)
    assert sorted(got["right_id"]) == [f"JE-{i:03d}" for i in range(config.CANDIDATE_CAP)]


def test_payment_cap_always_keeps_a_narration_reference():
    invoices = pd.DataFrame({
        "invoice_id": ["VEN001-0001"], "doc_type": ["INVOICE"], "invoice_type": ["PURCHASE"],
        "invoice_date": [pd.Timestamp("2025-06-01")], "party_id": ["VEN-001"], "invoice_total_paise": [100_000],
    })
    n = config.CANDIDATE_CAP + 5
    bank = pd.DataFrame({
        "txn_id": [f"TXN-{i:03d}" for i in range(n)], "direction": ["DEBIT"] * n,
        "txn_date": [pd.Timestamp("2025-06-20")] * n, "amount_paise": [100_000 + 1_000 * i for i in range(n)],
        "resolved_party_id": ["VEN-001"] * (n - 1) + [None],
        "narration": ["NEFT/U/ACME"] * (n - 1) + ["NEFT/U/SOMEONE ELSE/ven0010001"],
    })
    got = payment_candidates(invoices, bank)
    assert f"TXN-{n - 1:03d}" in set(got["right_id"])
    assert len(got) == config.CANDIDATE_CAP + 1
