import pytest

from ledgerlens_ml.parties import PartyResolver, resolve_bank


@pytest.fixture(scope="module")
def resolver(mini):
    return PartyResolver(mini.parties, mini.invoices)


# Real bank rows from the workbook: name, narration, direction, expected party, expected method.
ROWS = [
    ("FALCON SOLUTIONS & CO", "CHEQUE/ICIC251060001814/FALCON SOLUTIONS & CO/inv252600043", "CREDIT", "CUS-053", "invoice_ref"),
    ("DELTA FOODS", "NEFT/ICIC251130002633/DELTA FOODS/INV-2526-00130", "CREDIT", "CUS-016", "invoice_ref"),
    ("ZENITH COMPONENTS & CO", "NEFT/SBIN251180003129/ZENITH COMPONENTS & CO/VEN031-0001", "DEBIT", "VEN-031", "invoice_ref"),
    ("JUPITER INDUSTRIES PVT", "NEFT/HDFC251390002804/JUPITER INDUSTRIES PVT/VEN046-0002", "DEBIT", "VEN-046", "invoice_ref"),
    ("HORIZONLOGISTICS&CO", "NEFT/ICIC252720001904/HORIZONLOGISTICS&CO/INV-2526-01157,INV-2526-01165", "CREDIT", "CUS-058", "invoice_ref"),
    # Truncated name, no reference.
    ("JUPITER INDUSTRIES PVT", "CHEQUE/SBIN260840003468/JUPITER INDUSTRIES PVT", "DEBIT", "VEN-046", "name"),
    # Spaces dropped by the bank feed, no reference.
    ("HORIZONLOGISTICS&CO", "NEFT/SBIN251290001320/HORIZONLOGISTICS&CO", "CREDIT", "CUS-058", "name"),
    # Narration-only: the name says nothing.
    ("NEFT TRANSFER", "NEFT/UTIB251390004482/NEFT TRANSFER/VEN035-0002", "DEBIT", "VEN-035", "invoice_ref"),
    # A bare supplier serial must not be read as sales invoice 35; the name decides, and DEBIT prefers the supplier.
    ("ZENITH COMPONENTS & CO", "CHEQUE/SBIN260620002913/ZENITH COMPONENTS & CO/0035", "DEBIT", "VEN-031", "name"),
    ("HDFC BANK", "NEFT/HDFC260610004785/HDFC BANK/BANK CHARGES", "DEBIT", None, None),
]


@pytest.mark.parametrize("name, narration, direction, party, method", ROWS)
def test_resolver_on_hand_picked_rows(resolver, name, narration, direction, party, method):
    got_party, score, got_method = resolver.resolve(name, narration, direction)
    assert (got_party, got_method) == (party, method)
    assert 0 <= score <= 100
    if method == "name":
        assert score >= 88


def test_direction_breaks_a_tie_between_same_named_parties(resolver):
    assert resolver.resolve("ZENITH COMPONENTS", "NEFT/X/ZENITH COMPONENTS", "CREDIT")[0] == "CUS-057"
    assert resolver.resolve("ZENITH COMPONENTS", "NEFT/X/ZENITH COMPONENTS", "DEBIT")[0] == "VEN-031"


def test_a_sure_name_overrides_a_reference_to_another_party(resolver):
    # VEN046-0002 belongs to Jupiter Industries; the statement names Falcon Tech in full.
    party, _, method = resolver.resolve("FALCON TECH LLP", "NEFT/X/FALCON TECH LLP/VEN046-0002", "DEBIT")
    assert (party, method) == ("VEN-035", "name")


def test_resolve_bank_matches_links_truth(mini):
    resolved = resolve_bank(mini.bank, mini.parties, mini.invoices)
    assert list(resolved.columns[-3:]) == ["resolved_party_id", "resolve_score", "resolve_method"]
    truth = (
        mini.links.dropna(subset=["txn_id"])
        .merge(mini.invoices[["invoice_id", "party_id"]], on="invoice_id")
        .drop_duplicates("txn_id")
        .set_index("txn_id")["party_id"]
    )
    got = resolved.set_index("txn_id")["resolved_party_id"]
    assert (got.loc[truth.index] == truth).all()
    # Rows with no reference fall back to the account seen on referenced rows.
    assert resolved.set_index("txn_id").loc["TXN-000574", "resolve_method"] == "account"
    charges = resolved[resolved["narration"].str.contains("BANK CHARGES")]
    assert charges["resolved_party_id"].isna().all()
