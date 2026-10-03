from pathlib import Path

import pytest

from ledgerlens_ml import data

MINI = Path(__file__).parent / "fixtures" / "mini.xlsx"


@pytest.fixture(scope="session")
def mini(tmp_path_factory) -> data.Dataset:
    """About 280 invoices for 3 suppliers and 3 customers, without augmentation."""
    return data.load_dataset(MINI, derived_dir=tmp_path_factory.mktemp("no_derived"), expected_sha256=None)


@pytest.fixture(scope="session")
def full(tmp_path_factory) -> data.Dataset:
    """The real workbook without augmentation. Takes about 7 seconds, so only augment tests use it."""
    return data.load_dataset(derived_dir=tmp_path_factory.mktemp("no_derived_full"))
