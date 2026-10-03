"""Command line entry points: python -m ledgerlens_ml profile | augment."""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import config
from .augment import build_augmentation, write_augmentation
from .candidates import booking_candidates, candidate_recall, payment_candidates, true_pairs
from .data import Dataset, is_valid_gstin, load_dataset
from .features import booking_features, invoice_split, payment_features
from .matcher import save_artifact, train_matcher
from .normalise import narration_id_tokens
from .parties import resolve_bank

MATCHER_KINDS = ("booking", "payment")


def _pct(value: float) -> str:
    return f"{100 * value:.1f} percent"


def _train_recall(ds: Dataset, bank: pd.DataFrame) -> dict[str, tuple[float, int, pd.DataFrame]]:
    train_ids = set(ds.invoices.loc[invoice_split(ds.invoices) == "train", "invoice_id"])
    out = {}
    for kind, candidates in (("booking", booking_candidates(ds.invoices, ds.ledger)), ("payment", payment_candidates(ds.invoices, bank))):
        truth = true_pairs(ds.links, kind)
        truth = truth[truth["invoice_id"].isin(train_ids)]
        out[kind] = (candidate_recall(candidates, truth), len(truth), candidates)
    return out


def profile(_: argparse.Namespace) -> int:
    """Check the hash and column contract, then print the facts in ML_BUILD.md 3.3."""
    ds = load_dataset()
    print(f"Workbook {config.DATASET_PATH.name}: SHA-256 and column contract ok")
    rows = {"invoices": ds.invoices, "bank_transactions": ds.bank, "accounting_ledger": ds.ledger, "tax_rates": ds.tax_rates,
            "party_master": ds.parties, "tax_filings": ds.filings, "answer_key": ds.answer_key, "links": ds.links}
    print("Rows: " + ", ".join(f"{name} {len(frame):,}" for name, frame in rows.items())
          + f", labels {int((ds.labels['source'] == 'workbook').sum()):,}")
    if ds.gstr2b is None:
        print("GSTR-2B: not generated yet, run python -m ledgerlens_ml augment")
    else:
        print(f"GSTR-2B: {len(ds.gstr2b):,} lines, {int((ds.labels['source'] == 'augment').sum()):,} augment labels")

    purchases = ds.invoices[ds.invoices["invoice_type"] == "PURCHASE"]
    per_month = purchases.groupby(purchases["invoice_date"].dt.strftime("%Y-%m")).size()
    print(f"Purchase invoices per month: {per_month.min()} to {per_month.max()}; median per supplier {purchases.groupby('party_id').size().median():.0f}")
    print(f"Party GSTINs passing the check digit: {int(ds.parties['gstin'].map(is_valid_gstin).sum())} of {len(ds.parties)}")

    invoice_ids = set(ds.invoices["invoice_id"])
    tokens = ds.bank["narration"].map(narration_id_tokens)
    as_written = tokens.map(lambda ts: any(t.upper().removeprefix("INV ") in invoice_ids for t in ts))
    print(f"Bank narrations quoting an invoice ID as written: {_pct(as_written.mean())}; in another form (case, separators, serial only): {_pct((tokens.map(bool) & ~as_written).mean())}; no reference: {_pct((~tokens.map(bool)).mean())}")
    names = set(ds.parties["party_name"].str.upper())
    print(f"Bank counterparty names equal to a party master name: {_pct(ds.bank['counterparty_name'].isin(names).mean())}")
    refs = ds.ledger["invoice_ref"].dropna()
    print(f"Ledger invoice_ref values found in invoices: {_pct(refs.isin(set(ds.invoices['invoice_id'])).mean())}")

    paid = ds.links.dropna(subset=["txn_id"]).merge(ds.invoices[["invoice_id", "invoice_date", "invoice_total_paise", "party_id"]], on="invoice_id")
    paid = paid.merge(ds.bank[["txn_id", "txn_date", "amount_paise"]], on="txn_id")
    lag = (paid["txn_date"] - paid["invoice_date"]).dt.days
    print(f"Payment lag in days: min {lag.min()}, 5th percentile {lag.quantile(0.05):.0f}, median {lag.median():.0f}, 95th percentile {lag.quantile(0.95):.0f}, max {lag.max()}")
    full = paid[paid["link_type"] == "FULL"]
    ratio = full["amount_paise"] / full["invoice_total_paise"]
    print(f"FULL links, payment divided by invoice total: median {ratio.median():.3f}, min {ratio.min():.3f}, max {ratio.max():.3f}")
    print(f"Most bank transactions per invoice: {paid.groupby('invoice_id')['txn_id'].nunique().max()}; most invoices per bank transaction: {paid.groupby('txn_id')['invoice_id'].nunique().max()}")

    bank = resolve_bank(ds.bank, ds.parties, ds.invoices)
    truth = paid.drop_duplicates("txn_id").set_index("txn_id")["party_id"]
    resolved = bank.set_index("txn_id")["resolved_party_id"]
    print(f"Counterparty resolution on linked bank transactions: {_pct((resolved.loc[truth.index] == truth).mean())} correct; methods {bank['resolve_method'].fillna('none').value_counts().to_dict()}")

    gate_ok = True
    recalls = _train_recall(ds, bank)
    for kind, (recall, n_truth, candidates) in recalls.items():
        ok = recall >= config.CANDIDATE_RECALL_GATE
        gate_ok &= ok
        print(f"Candidate recall, {kind}, train: {_pct(recall)} of {n_truth:,} true pairs, {len(candidates):,} candidates ({'passes' if ok else 'fails'} the {_pct(config.CANDIDATE_RECALL_GATE)} gate)")

    pd.set_option("display.width", 200)
    for kind, frame in (("booking", booking_features(recalls["booking"][2], ds.invoices, ds.ledger)), ("payment", payment_features(recalls["payment"][2], ds.invoices, bank))):
        print(f"\nFeature frame, {kind}: {len(frame):,} rows; columns with missing values: {sorted(frame.columns[frame.isna().any()])}")
        print(frame.describe().T[["mean", "min", "50%", "max"]].round(3).to_string())
    return 0 if gate_ok else 1


def augment(_: argparse.Namespace) -> int:
    """Write data/derived/gstr2b.csv, augment_labels.csv and augment_manifest.json."""
    ds = load_dataset(derived_dir=config.DERIVED_DIR / "_none")
    aug = build_augmentation(ds)
    out_dir = write_augmentation(aug)
    counts = aug.manifest["counts"]
    print(f"Wrote {counts['gstr2b_lines']:,} GSTR-2B lines and {len(aug.labels):,} labels to {out_dir}")
    print(f"Labels: {counts['labels']}")
    return 0


def _print_card(card: dict) -> None:
    test = card["test"]
    print(f"\nmatcher_{card['kind']}: shipped {card['shipped']}, {card['best_iteration']} trees, thresholds {card['thresholds']}, rows {card['rows']}")
    for row in card["targets"]:
        actual = "n/a" if row["actual"] is None else f"{row['actual']:.4f}"
        print(f"  {row['metric']:<20} target {row['target']:.2f}  actual {actual}  {'n/a' if row['met'] is None else 'pass' if row['met'] else 'miss'}")
    print(f"  test pair level: {({k: round(v, 4) if isinstance(v, float) else v for k, v in test['pair'].items()})}")
    print(f"  baseline F1 {test['baseline']['f1']:.4f}, model F1 {test['model']['f1']:.4f}, gain {test['f1_gain_over_baseline']:+.4f}")
    print(f"  invoice level: {test['invoice_level']}")
    print(f"  hard cases: {test['hard_cases']}")
    print(f"  benign traps: {test['benign_traps']}")
    print(f"  top features: {list(card['feature_importance'])[:5]}")


def train(args: argparse.Namespace) -> int:
    """Train matchers and write artifacts and cards to ml/artifacts."""
    ds = load_dataset()
    kinds = MATCHER_KINDS if args.all else (args.model,)
    for kind in kinds:
        artifact, card = train_matcher(kind, ds)
        out_dir = save_artifact(artifact, card)
        _print_card(card)
        print(f"  wrote {out_dir / f'matcher_{kind}.joblib'} and its card")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledgerlens_ml", description="LedgerLens ML tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("profile", help="check the workbook and print dataset facts").set_defaults(run=profile)
    commands.add_parser("augment", help="generate GSTR-2B lines and augment labels").set_defaults(run=augment)
    train_parser = commands.add_parser("train", help="train a model and write its artifact and card")
    which = train_parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--model", choices=MATCHER_KINDS)
    which.add_argument("--all", action="store_true")
    train_parser.set_defaults(run=train)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
