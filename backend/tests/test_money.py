from app.engine.money import summarise
from app.engine.one_to_many import find_subset

BASE = {"period": "2025-09", "output": {"igst": 1000, "cgst": 500, "sgst": 500}, "itc": {"igst": 600, "cgst": 200, "sgst": 200},
        "declared": {"output_paise": 2000, "itc_paise": 1000, "net_paise": 1000, "filed_on": "2025-10-20", "due_on": "2025-10-20"},
        "invoice_count": 10, "match_counts": {"auto": 9, "review": 1, "unmatched": 0, "one_to_many": 0, "open": 0}}


def finding(finding_type, impact_type, impacts, status="open", category="tax"):
    return {"finding_type": finding_type, "category": category, "severity": "high", "status": status, "impact_type": impact_type,
            "impact_paise": sum(sum(share.values()) for share in impacts.values()), "evidence": {"impacts": impacts}}


def test_no_findings_gives_the_books():
    out = summarise(BASE, [])
    assert (out["itc_at_risk_paise"], out["itc_found_paise"], out["net_payable_paise"]) == (0, 0, 1000)
    assert out["liability"]["gap_paise"] == 0


def test_two_findings_on_one_invoice_count_once():
    both = [finding("MISSING_IN_2B", "itc_at_risk", {"V1": {"igst": 100}}), finding("CANCELLED_GSTIN", "itc_at_risk", {"V1": {"igst": 100}}),
            finding("RULE_37_UNPAID_180", "itc_at_risk", {"V2": {"cgst": 20, "sgst": 20}})]
    out = summarise(BASE, both)
    assert out["itc_at_risk_paise"] == 140
    assert sum(c["paise"] for c in out["itc_at_risk_by_cause"]) == 140
    assert out["net_payable_paise"] == 1000 + 140
    eligible = {row["tax_type"]: row["eligible_itc_paise"] for row in out["liability"]["by_tax_type"]}
    assert eligible == {"igst": 500, "cgst": 180, "sgst": 180}


def test_approving_excess_tax_lowers_net_payable_and_closes_the_finding():
    hero = finding("WRONG_TAX_RATE", "excess_tax", {"S1": {"igst": 300}})
    before = summarise(BASE, [hero])
    after = summarise(BASE, [dict(hero, status="approved")])
    assert (before["excess_tax_paise"], after["excess_tax_paise"]) == (300, 0)
    assert after["net_payable_paise"] == before["net_payable_paise"] - 300


def test_status_rules_for_credit():
    at_risk = finding("MISSING_IN_2B", "itc_at_risk", {"V1": {"igst": 100}})
    found = finding("MISSING_IN_BOOKS", "itc_found", {"2B-1": {"igst": 50}}, category="missing")
    assert summarise(BASE, [dict(at_risk, status="approved")])["itc_at_risk_paise"] == 0
    assert summarise(BASE, [dict(at_risk, status="approved")])["net_payable_paise"] == 1100
    assert summarise(BASE, [dict(at_risk, status="dismissed")])["net_payable_paise"] == 1000
    assert summarise(BASE, [found])["itc_found_paise"] == 50
    assert summarise(BASE, [dict(found, status="approved")])["net_payable_paise"] == 950
    filed = finding("ITC_OVERCLAIM", "itc_at_risk", {"2025-09": {"other": 400}}, category="filing")
    assert summarise(BASE, [filed])["itc_at_risk_paise"] == 400
    assert summarise(BASE, [filed])["net_payable_paise"] == 1000


def test_subset_sum_prefers_fewest_then_earliest():
    assert find_subset([500, 300, 200, 800], 800) == (3,)
    assert find_subset([500, 300, 200], 800) == (0, 1)
    assert find_subset([500, 300, 200], 1000) == (0, 1, 2)
    assert find_subset([500, 300], 1_000) is None
    assert find_subset([50_000, 30_050], 80_000, tolerance=100) == (0, 1)
