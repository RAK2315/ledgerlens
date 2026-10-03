"""One-off script: writes mini.xlsx, every record of 3 suppliers and 3 customers picked with seed 7.

Run from the repo root: ml\\.venv\\Scripts\\python ml\\tests\\fixtures\\make_mini.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from ledgerlens_ml import config

OUT = Path(__file__).parent / "mini.xlsx"


def main() -> None:
    sheets = pd.read_excel(config.DATASET_PATH, sheet_name=None)
    rng = np.random.default_rng(7)
    master = sheets["party_master"].sort_values("party_id")
    chosen = []
    for party_type in ("VENDOR", "CUSTOMER"):
        ids = master.loc[master["party_type"] == party_type, "party_id"].to_numpy()
        chosen.extend(rng.choice(ids, size=3, replace=False))

    invoices = sheets["invoices"][sheets["invoices"]["party_id"].isin(chosen)]
    links = sheets["links"][sheets["links"]["invoice_id"].isin(invoices["invoice_id"])]
    bank = sheets["bank_transactions"]
    accounts = bank.loc[bank["txn_id"].isin(links["txn_id"]), "counterparty_account"].unique()
    bank = bank[bank["counterparty_account"].isin(accounts) | bank["narration"].str.contains("BANK CHARGES")]
    ledger = sheets["accounting_ledger"]
    linked_entries = set(links["booking_entry_id"].dropna()) | set(links["receipt_entry_id"].dropna())
    ledger = ledger[ledger["party_id"].isin(chosen) | ledger["entry_id"].isin(linked_entries)]
    entities = set(invoices["invoice_id"]) | set(bank["txn_id"]) | set(ledger["entry_id"])
    labels = sheets["labels"][sheets["labels"]["entity_id"].isin(entities)]

    sheets.update(invoices=invoices, links=links, bank_transactions=bank, accounting_ledger=ledger, labels=labels)
    with pd.ExcelWriter(OUT) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    print({name: len(frame) for name, frame in sheets.items()}, "parties", chosen)


if __name__ == "__main__":
    main()
