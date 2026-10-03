"""The Proof page's numbers: catch rate and false alarms per Finding type, every miss, the months, and the matcher cards."""
from __future__ import annotations

import json
from functools import lru_cache

from ledgerlens_ml import TEST_MONTHS

from . import db, settings
from .engine import analyse, evaluate
from .engine.labels import META

MATCHERS = (("booking", "Invoice to ledger match"), ("payment", "Invoice to bank match"))
# The ring is one label for the year, so it cannot be split by month.
NOT_MONTHLY = {"PAN_LINKED_RING"}


def _card(kind: str) -> dict:
    return json.loads((settings.REPO_ROOT / "ml" / "artifacts" / f"matcher_{kind}.card.json").read_text(encoding="utf-8"))


def _matcher_row(kind: str, name: str) -> dict:
    pair = _card(kind)["test"]["pair"]
    auto = round(pair["positives"] * pair["recall"])
    wrong = round(auto / pair["precision"] - auto) if pair["precision"] else 0
    return {"finding_type": f"MATCH_{kind.upper()}", "label": name, "planted": pair["positives"], "caught": auto, "reported": auto + wrong,
            "false_alarms": wrong, "on_benign_traps": 0, "catch_rate": pair["recall"], "false_alarm_rate": pair["false_auto_rate"], "source": "ml"}


def _matcher(kind: str, name: str) -> dict:
    card = _card(kind)
    test = card["test"]
    return {"kind": kind, "name": name, "rows": card["rows"], "model": test["model"], "baseline": test["baseline"],
            "hard_cases": test["hard_cases"], "benign_traps": test["benign_traps"], "invoice_level": test["invoice_level"]}


def _text(value) -> str | None:
    return None if value is None or value != value else str(value)


@lru_cache(maxsize=2)
def report(scope: str) -> dict:
    """scope is test (the unseen months) or year (every month)."""
    result, _ = analyse.analysis()
    ds = analyse.dataset()
    raw = [r for r in evaluate.evaluate(ds, result.findings, TEST_MONTHS if scope == "test" else None) if r["planted"] or r["reported"]]
    rows = [{**{k: v for k, v in r.items() if k not in ("missed", "false_alarm_ids")}, "label": META[r["finding_type"]][0], "source": "engine"} for r in raw]
    if scope == "test":
        rows += [_matcher_row(kind, name) for kind, name in MATCHERS]

    reported = {(f["finding_type"], f["entity_id"]): f for f in result.findings}
    misses = []
    for r in raw:
        kind_label = META[r["finding_type"]][0]
        planted = ds.labels[ds.labels["issue_type"] == r["finding_type"]].drop_duplicates("entity_id").set_index("entity_id")
        for entity in r["missed"]:
            label = planted.loc[entity]
            misses.append({"finding_type": r["finding_type"], "label": kind_label, "kind": "missed", "entity_id": entity, "detail": _text(label["description"]),
                           "expected": _text(label["expected_value"]), "recorded": _text(label["recorded_value"])})
        for entity in r["false_alarm_ids"]:
            finding = reported.get((r["finding_type"], entity))
            misses.append({"finding_type": r["finding_type"], "label": kind_label, "kind": "false_alarm", "entity_id": entity,
                           "detail": f"{finding['title']}. {finding['reason']}" if finding else None, "expected": None, "recorded": None})

    by_month = []
    for period in sorted(ds.filings["period"]):
        month = [r for r in evaluate.evaluate(ds, result.findings, (period,)) if r["finding_type"] not in NOT_MONTHLY]
        by_month.append({"period": period, "unseen": period in TEST_MONTHS, **{k: sum(r[k] for r in month) for k in ("planted", "caught", "reported", "false_alarms")}})

    return {"split": scope, "months": list(TEST_MONTHS) if scope == "test" else [m["period"] for m in by_month], "rows": rows, "misses": misses,
            "by_month": by_month, "matchers": [_matcher(kind, name) for kind, name in MATCHERS], "generated_at": db.now()}
