import json

import pandas as pd
import pytest

from ledgerlens_ml import config, data
from ledgerlens_ml.augment import build_augmentation, write_augmentation
from ledgerlens_ml.normalise import id_serial


@pytest.fixture(scope="module")
def aug(full):
    return build_augmentation(full)


@pytest.fixture(scope="module")
def purchases(full):
    inv = full.invoices
    return inv[(inv["invoice_type"] == "PURCHASE") & (inv["doc_type"] == "INVOICE")]


def labels_of(aug, issue_type):
    return aug.labels[aug.labels["issue_type"] == issue_type]


def test_same_seed_gives_byte_identical_files(full, aug, tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    write_augmentation(aug, first)
    write_augmentation(build_augmentation(full), second)
    for name in ("gstr2b.csv", "augment_labels.csv", "augment_manifest.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_written_files_load_back_unchanged(full, aug, tmp_path):
    write_augmentation(aug, tmp_path)
    pd.testing.assert_frame_equal(data.read_gstr2b(tmp_path / "gstr2b.csv"), aug.gstr2b)
    pd.testing.assert_frame_equal(data.read_augment_labels(tmp_path / "augment_labels.csv"), aug.labels)
    assert json.loads((tmp_path / "augment_manifest.json").read_text(encoding="utf-8")) == aug.manifest
    assert aug.manifest["source_sha256"] == full.sha256
    assert aug.manifest["seed"] == config.SEED


def test_filing_behaviour_split(full, aug):
    behaviour = pd.Series(aug.manifest["filing_behaviour"])
    suppliers = full.parties.loc[full.parties["party_type"] == "VENDOR", "party_id"]
    assert sorted(behaviour.index) == sorted(suppliers)
    assert behaviour.value_counts().to_dict() == {"reliable": 35, "late": 10, "non_filer": 5}


def test_lines_follow_filing_behaviour(aug, purchases):
    behaviour = purchases["party_id"].map(aug.manifest["filing_behaviour"])
    duplicates = set(aug.manifest["duplicate_invoices_skipped"])
    lines = aug.gstr2b.dropna(subset=["source_invoice_id"]).set_index("source_invoice_id")
    assert lines.index.is_unique

    non_filed = purchases[behaviour == "non_filer"]
    assert not lines.index.isin(non_filed["invoice_id"]).any()
    missing = labels_of(aug, "MISSING_IN_2B").set_index("entity_id")["financial_impact_paise"]
    expected = non_filed[~non_filed["invoice_id"].isin(duplicates)].set_index("invoice_id")["total_tax_paise"]
    assert missing.sort_index().astype("int64").to_dict() == expected.sort_index().to_dict()

    filed = purchases[(behaviour != "non_filer") & ~purchases["invoice_id"].isin(duplicates)]
    assert sorted(lines.index) == sorted(filed["invoice_id"])
    assert not lines.index.isin(duplicates).any()

    late = purchases[behaviour == "late"].set_index("invoice_id")
    late = late[late.index.isin(lines.index)]
    next_month = (late["invoice_date"].dt.to_period("M") + 1).dt.strftime("%m%Y")
    assert (lines.loc[late.index, "return_period"] == next_month).all()


def test_variation_rates_within_one_percent(aug, purchases):
    lines = aug.gstr2b.dropna(subset=["source_invoice_id"])
    counts = aug.manifest["counts"]
    assert abs(counts["id_variants"] / len(lines) - config.AUGMENT_ID_VARIANT_RATE) <= 0.01
    assert abs(counts["value_mismatches"] / len(lines) - config.AUGMENT_VALUE_MISMATCH_RATE) <= 0.01
    assert abs(counts["date_shifts"] / len(lines) - config.AUGMENT_DATE_SHIFT_RATE) <= 0.01
    assert counts["value_mismatches"] == len(labels_of(aug, "GSTR2B_VALUE_MISMATCH"))
    extra = aug.gstr2b[aug.gstr2b["source_invoice_id"].isna()]
    assert len(extra) == round(config.AUGMENT_EXTRA_LINE_RATE * len(purchases))
    assert sorted(labels_of(aug, "MISSING_IN_BOOKS")["entity_id"]) == sorted(extra["line_id"])


def test_supplier_format_ids_keep_the_serial(aug):
    lines = aug.gstr2b.dropna(subset=["source_invoice_id"])
    assert (lines["invoice_number"].map(id_serial) == lines["source_invoice_id"].map(id_serial)).all()
    changed = lines[lines["invoice_number"] != lines["source_invoice_id"]]
    assert len(changed) == aug.manifest["counts"]["id_variants"]


def test_value_mismatch_impact_is_the_tax_difference(aug, purchases):
    lines = aug.gstr2b.dropna(subset=["source_invoice_id"]).set_index("source_invoice_id")
    booked = purchases.set_index("invoice_id")
    for label in labels_of(aug, "GSTR2B_VALUE_MISMATCH").itertuples():
        line, invoice = lines.loc[label.entity_id], booked.loc[label.entity_id]
        line_tax = line["igst_paise"] + line["cgst_paise"] + line["sgst_paise"]
        ratio = line["taxable_value_paise"] / invoice["taxable_value_paise"]
        assert 0.02 <= abs(ratio - 1) <= 0.15 + 1e-6
        assert label.financial_impact_paise == abs(invoice["total_tax_paise"] - line_tax)
    untouched = lines[~lines.index.isin(labels_of(aug, "GSTR2B_VALUE_MISMATCH")["entity_id"])]
    assert (untouched["taxable_value_paise"] == booked.loc[untouched.index, "taxable_value_paise"]).all()


def test_every_gstin_passes_the_check_digit(full, aug):
    assert aug.gstr2b["gstin_supplier"].map(data.is_valid_gstin).all()
    assert set(aug.gstr2b["gstin_supplier"]) <= set(full.parties["gstin"])
    for ring in aug.manifest["pan_rings"]:
        assert data.is_valid_gstin(ring["new_gstin"])
        assert ring["new_gstin"][2:12] == ring["shared_pan"] == ring["new_pan"]
        assert ring["new_gstin"][:2] == ring["old_gstin"][:2]


def test_rule_37_labels(full, aug, purchases):
    unpaid = full.links.loc[full.links["link_type"] == "UNPAID_OPEN", "invoice_id"]
    cutoff = pd.Timestamp(config.FY_END) - pd.Timedelta(days=config.RULE_37_DAYS)
    old = purchases[purchases["invoice_id"].isin(unpaid) & (purchases["invoice_date"] < cutoff)]
    labels = labels_of(aug, "RULE_37_UNPAID_180")
    assert len(old) > 0
    assert sorted(labels["entity_id"]) == sorted(old["invoice_id"])
    assert labels.set_index("entity_id")["financial_impact_paise"].astype("int64").to_dict() == old.set_index("invoice_id")["total_tax_paise"].to_dict()


def test_cancelled_suppliers(aug, purchases):
    cancelled = aug.manifest["cancelled_suppliers"]
    assert len(cancelled) == config.AUGMENT_CANCELLED_SUPPLIERS
    labelled = set(labels_of(aug, "CANCELLED_GSTIN")["entity_id"])
    expected = set()
    for item in cancelled:
        assert aug.manifest["filing_behaviour"][item["party_id"]] == "non_filer"
        theirs = purchases[purchases["party_id"] == item["party_id"]]
        after = theirs[theirs["invoice_date"] >= pd.Timestamp(item["cancelled_from"])]
        assert 0 < len(after) < len(theirs)
        expected |= set(after["invoice_id"])
    assert labelled == expected


def test_pan_ring_links_one_supplier_and_one_customer(full, aug):
    (ring,) = aug.manifest["pan_rings"]
    types = full.parties.set_index("party_id")["party_type"]
    assert types[ring["supplier_party_id"]] == "VENDOR"
    assert types[ring["customer_party_id"]] == "CUSTOMER"
    assert aug.manifest["filing_behaviour"][ring["supplier_party_id"]] == "reliable"
    assert sorted(labels_of(aug, "PAN_LINKED_RING")["entity_id"]) == sorted([ring["supplier_party_id"], ring["customer_party_id"]])


def test_manifest_applies_to_parties_and_invoices(full, aug):
    parties, invoices = data.apply_manifest(full.parties, full.invoices, aug.manifest)
    (ring,) = aug.manifest["pan_rings"]
    by_id = parties.set_index("party_id")
    assert by_id.loc[ring["customer_party_id"], "pan"] == by_id.loc[ring["supplier_party_id"], "pan"]
    assert (by_id["gstin_status"] == "cancelled").sum() == config.AUGMENT_CANCELLED_SUPPLIERS
    assert by_id["cancelled_from"].notna().sum() == config.AUGMENT_CANCELLED_SUPPLIERS
    assert by_id["gstin"].map(data.is_valid_gstin).all()
    assert by_id["filing_behaviour"].notna().sum() == 50
    theirs = invoices[invoices["party_id"] == ring["customer_party_id"]]
    assert (theirs["party_gstin"] == ring["new_gstin"]).mean() > 0.9
    # Planted invalid GSTINs on invoices stay as they are.
    invalid = full.labels.loc[full.labels["issue_type"] == "INVALID_GSTIN", "entity_id"]
    before = full.invoices.set_index("invoice_id").loc[invalid, "party_gstin"]
    after = invoices.set_index("invoice_id").loc[invalid, "party_gstin"]
    assert (before == after).all()


def test_load_dataset_reads_the_derived_files(mini, tmp_path):
    from conftest import MINI

    small = build_augmentation(mini)
    write_augmentation(small, tmp_path)
    ds = data.load_dataset(MINI, derived_dir=tmp_path, expected_sha256=None)
    pd.testing.assert_frame_equal(ds.gstr2b, small.gstr2b)
    assert (ds.labels["source"] == "augment").sum() == len(small.labels)
    assert ds.manifest == small.manifest
    with pytest.raises(data.DatasetError):
        data.load_dataset(derived_dir=tmp_path)
