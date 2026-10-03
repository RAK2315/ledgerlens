"""Print the engine's Catch rate per Finding type for the whole year, then the September 2025 summary.

Run from the repo root: backend\\.venv\\Scripts\\python backend\\scripts\\check_engine.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine import analyse, evaluate, money  # noqa: E402
from app.engine.findings import rupees  # noqa: E402

start = time.time()
result, cached = analyse.analysis(lambda stage, status, message: print(f"  {stage:<10} {status:<8} {message}"))
print(f"analysis in {time.time() - start:.1f}s (cached: {cached}); {len(result.findings):,} Findings, {len(result.matches):,} Matches\n")

print(f"{'finding type':<28}{'planted':>8}{'caught':>8}{'reported':>9}{'false':>7}{'benign':>7}{'catch':>7}")
for row in evaluate.evaluate(analyse.dataset(), result.findings):
    rate = "" if row["catch_rate"] is None else f"{row['catch_rate']:.2f}"
    print(f"{row['finding_type']:<28}{row['planted']:>8}{row['caught']:>8}{row['reported']:>9}{row['false_alarms']:>7}{row['on_benign_traps']:>7}{rate:>7}")

period = sys.argv[1] if len(sys.argv) > 1 else "2025-09"
found = [dict(f, status="open") for f in result.findings if f["period"] == period]
summary = money.summarise(money.base(analyse.books(), period, result.matches), found)
print(f"\n{period}: {len(found)} Findings")
for key in ("itc_at_risk_paise", "itc_found_paise", "excess_tax_paise", "short_tax_paise", "net_payable_paise"):
    print(f"  {key:<20} {rupees(summary[key])}")
print("  match counts", summary["match_counts"])
print("  by category", summary["finding_counts_by_category"])
print("  ITC at risk by cause", [(c["label"], rupees(c["paise"])) for c in summary["itc_at_risk_by_cause"]])
print("  liability", summary["liability"])
for f in summary["top_findings"]:
    print("  top:", f["finding_type"], rupees(f["impact_paise"]), "|", f["title"])
hero = [f for f in found if f["entity_id"] == "INV-2526-01431"]
print("  hero:", [(f["finding_type"], f["impact_type"], rupees(f["impact_paise"]), f["reason"]) for f in hero])
