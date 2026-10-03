import pytest
from rapidfuzz.distance import DamerauLevenshtein

from ledgerlens_ml.normalise import (
    id_serial,
    narration_id_tokens,
    normalise_invoice_id,
    normalise_party_name,
)


@pytest.mark.parametrize(
    "raw, normalised, serial",
    [
        ("INV-2526-02759", "2759", "2759"),
        ("INV-2425-02759", "2759", "2759"),
        ("INV-2526-O2328", "2328", "2328"),
        ("INV-252-02921", "2522921", "2921"),
        ("VEN042-0001", "VEN0421", "1"),
        ("ven0420001", "VEN0421", "1"),
        ("INV VEN002-0001", "VEN0021", "1"),
        ("VEN/001/0001", "VEN0011", "1"),
        ("inv252601229", "1229", "1229"),
        ("INV INV-2526-00473", "473", "473"),
        ("INV/2526-00473", "473", "473"),
        ("INV-2526-0O328", "328", "328"),
        ("CN-2526-0038", "CN38", "38"),
        ("01012", "1012", "1012"),
    ],
)
def test_invoice_id_table(raw, normalised, serial):
    assert normalise_invoice_id(raw) == normalised
    assert id_serial(raw) == serial


def test_dropped_digit_is_caught_by_serial_and_edit_distance():
    assert id_serial("INV-252-02921") == id_serial("INV-2526-02921")
    assert DamerauLevenshtein.distance("INV-252-02921", "INV-2526-02921") == 1


def test_empty_and_missing_ids():
    assert normalise_invoice_id(None) == ""
    assert normalise_invoice_id("  ") == ""
    assert id_serial(None) == ""
    assert id_serial("BANK CHARGES") == ""


@pytest.mark.parametrize(
    "bank_name, master_name",
    [
        ("EVERGREEN INFRA PRIVATE LIMITED", "Evergreen Infra Private Limited"),
        ("JUPITER COMPONENTS PVT LTD", "Jupiter Components Pvt Ltd"),
        ("BHARATSYSTEMSPVTLTD", "Bharat Systems Pvt Ltd"),
        ("LOTUSINFRA&CO", "Lotus Infra & Co"),
        ("VERTEXLOGISTICSLLP", "Vertex Logistics LLP"),
        ("APEXFOODSPRIVATELIMITED", "Apex Foods Private Limited"),
    ],
)
def test_party_name_pairs_from_the_data(bank_name, master_name):
    left = normalise_party_name(bank_name).replace(" ", "")
    right = normalise_party_name(master_name).replace(" ", "")
    assert left == right


def test_party_name_strips_legal_suffixes_and_punctuation():
    assert normalise_party_name("Evergreen Infra & Co") == "EVERGREEN INFRA"
    assert normalise_party_name("Nova Systems Pvt. Ltd.") == "NOVA SYSTEMS"
    assert normalise_party_name("Sigma Traders Limited") == "SIGMA TRADERS"
    assert normalise_party_name(None) == ""


@pytest.mark.parametrize(
    "narration, tokens",
    [
        ("CHEQUE/ICIC250930003435/GLOBAL CONSULTING PVT LTD/VEN001-0001", ["VEN001-0001"]),
        ("NEFT/HDFC250940003661/JUPITER COMPONENTS PVT LTD/INV VEN002-0001", ["INV VEN002-0001"]),
        ("NEFT/X/STERLING INFRA LTD/INV-2526-00001,INV-2526-00002", ["INV-2526-00001", "INV-2526-00002"]),
        ("NEFT/HDFC251110004743/UNITY LOGISTICS LTD", []),
        ("RTGS/SBIN251180004764/PAYROLL ACCOUNT/SALARY APR2025", []),
        ("NEFT/HDFC260610004785/HDFC BANK/BANK CHARGES", []),
        ("NEFT/SBIN251420001852/GLOBAL RETAIL & CO/00115", ["00115"]),
    ],
)
def test_narration_id_tokens(narration, tokens):
    assert narration_id_tokens(narration) == tokens
