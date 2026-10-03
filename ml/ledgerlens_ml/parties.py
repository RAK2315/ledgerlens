"""Resolve bank counterparties to party_id (ML_BUILD.md 4.2)."""
from __future__ import annotations

from collections import Counter

import pandas as pd
from rapidfuzz import fuzz

from . import config
from .normalise import narration_id_tokens, normalise_invoice_id, normalise_party_name

DIRECTION_INVOICE_TYPE = {"DEBIT": "PURCHASE", "CREDIT": "SALES"}
DIRECTION_PARTY_TYPE = {"DEBIT": "VENDOR", "CREDIT": "CUSTOMER"}
# A bank name this sure overrides an invoice reference that points at another party (a mistyped reference).
NAME_OVERRIDES_REF_SCORE = 95


def _canonical(name: str) -> str:
    """Uppercase name with the legal suffix kept in one spelling, spaces removed. Used to break ties."""
    text = name.upper().replace("&", "AND").replace("PRIVATE", "PVT").replace("LIMITED", "LTD")
    return "".join(ch for ch in text if ch.isalnum())


class PartyResolver:
    def __init__(self, parties: pd.DataFrame, invoices: pd.DataFrame):
        self._parties = [
            (row.party_id, row.party_type, normalise_party_name(row.party_name), _canonical(row.party_name))
            for row in parties.itertuples()
        ]
        self._ref_to_party: dict[tuple[str, str], str | None] = {}
        for row in invoices.itertuples():
            key = (row.invoice_type, normalise_invoice_id(row.invoice_id))
            # Two parties behind one normalised ID means the reference proves nothing.
            self._ref_to_party[key] = row.party_id if self._ref_to_party.get(key, row.party_id) == row.party_id else None
        self._account_to_party: dict[str, str] = {}
        self._name_cache: dict[tuple[str, str | None], tuple[str | None, float]] = {}

    def _by_ref(self, narration: object, direction: str | None) -> str | None:
        types = [DIRECTION_INVOICE_TYPE[direction]] if direction in DIRECTION_INVOICE_TYPE else ["PURCHASE", "SALES"]
        found = set()
        for token in narration_id_tokens(narration):
            for invoice_type in types:
                party = self._ref_to_party.get((invoice_type, normalise_invoice_id(token)))
                if party:
                    found.add(party)
        return found.pop() if len(found) == 1 else None

    def _by_name(self, name: object, direction: str | None) -> tuple[str | None, float]:
        key = (name, direction)
        if key in self._name_cache:
            return self._name_cache[key]
        norm = normalise_party_name(name)
        best: tuple[float, bool, float, str] | None = None
        if norm:
            compact, canonical = norm.replace(" ", ""), _canonical(name)
            for party_id, party_type, party_norm, party_canonical in self._parties:
                score = max(fuzz.token_set_ratio(norm, party_norm), fuzz.ratio(compact, party_norm.replace(" ", "")))
                rank = (score, party_type == DIRECTION_PARTY_TYPE.get(direction), fuzz.ratio(canonical, party_canonical), party_id)
                if best is None or rank[:3] > best[:3]:
                    best = rank
        result = (best[3], float(best[0])) if best and best[0] >= config.NAME_MATCH_MIN_SCORE else (None, float(best[0]) if best else 0.0)
        self._name_cache[key] = result
        return result

    def learn_accounts(self, bank: pd.DataFrame) -> None:
        """Remember which party each counterparty account paid invoices for, from rows with a clear invoice reference."""
        votes: dict[str, Counter] = {}
        for row in bank.itertuples():
            party = self._by_ref(row.narration, row.direction)
            if party:
                votes.setdefault(row.counterparty_account, Counter())[party] += 1
        self._account_to_party = {account: counts.most_common(1)[0][0] for account, counts in votes.items()}

    def resolve(self, name: object, narration: object, direction: str | None = None, account: str | None = None) -> tuple[str | None, float, str | None]:
        """Return (party_id or None, score 0 to 100, method: invoice_ref, account or name)."""
        ref_party = self._by_ref(narration, direction)
        name_party, name_score = self._by_name(name, direction)
        account_party = self._account_to_party.get(account) if account else None
        if ref_party:
            if name_party and name_party != ref_party and name_score >= NAME_OVERRIDES_REF_SCORE and account_party != ref_party:
                return (account_party or name_party), name_score, ("account" if account_party else "name")
            return ref_party, 100.0, "invoice_ref"
        if account_party:
            return account_party, 100.0, "account"
        if name_party:
            return name_party, name_score, "name"
        return None, name_score, None


def resolve_bank(bank: pd.DataFrame, parties: pd.DataFrame, invoices: pd.DataFrame) -> pd.DataFrame:
    """Bank frame plus resolved_party_id, resolve_score and resolve_method."""
    resolver = PartyResolver(parties, invoices)
    resolver.learn_accounts(bank)
    resolved = [resolver.resolve(r.counterparty_name, r.narration, r.direction, r.counterparty_account) for r in bank.itertuples()]
    out = bank.copy()
    out["resolved_party_id"] = pd.Series([r[0] for r in resolved], index=bank.index, dtype="object")
    out["resolve_score"] = [r[1] for r in resolved]
    out["resolve_method"] = pd.Series([r[2] for r in resolved], index=bank.index, dtype="object")
    return out
