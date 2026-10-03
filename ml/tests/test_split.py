import pandas as pd

from ledgerlens_ml import config
from ledgerlens_ml.features import invoice_split, train_aggregates


def test_no_invoice_in_two_splits(mini):
    split = invoice_split(mini.invoices)
    assert split.index.equals(mini.invoices.index)
    assert set(split.dropna()) == {"train", "validation", "test"}
    months = mini.invoices["invoice_date"].dt.strftime("%Y-%m")
    for name, expected in (("train", config.TRAIN_MONTHS), ("validation", config.VALIDATION_MONTHS), ("test", config.TEST_MONTHS)):
        assert set(months[split == name]) <= set(expected)
    by_invoice = pd.DataFrame({"invoice_id": mini.invoices["invoice_id"], "split": split})
    assert by_invoice.groupby("invoice_id")["split"].nunique().max() == 1
    assert not set(config.TRAIN_MONTHS) & set(config.VALIDATION_MONTHS + config.TEST_MONTHS)
    assert not set(config.VALIDATION_MONTHS) & set(config.TEST_MONTHS)


def test_aggregates_read_train_rows_only(mini):
    baseline = train_aggregates(mini.invoices)
    changed = mini.invoices.copy()
    later = invoice_split(changed) != "train"
    changed.loc[later, "taxable_value_paise"] = changed.loc[later, "taxable_value_paise"] * 1000
    assert train_aggregates(changed) == baseline

    moved = mini.invoices.copy()
    in_train = invoice_split(moved) == "train"
    moved.loc[in_train, "taxable_value_paise"] = moved.loc[in_train, "taxable_value_paise"] * 2
    assert train_aggregates(moved) != baseline


def test_aggregates_shape(mini):
    agg = train_aggregates(mini.invoices)
    assert set(agg) == {"party_median_taxable_paise", "party_train_count", "category_median_taxable_paise", "taxable_p95_paise"}
    train = mini.invoices[(invoice_split(mini.invoices) == "train") & (mini.invoices["doc_type"] == "INVOICE")]
    party = train["party_id"].iloc[0]
    assert agg["party_median_taxable_paise"][party] == float(train.loc[train["party_id"] == party, "taxable_value_paise"].median())
