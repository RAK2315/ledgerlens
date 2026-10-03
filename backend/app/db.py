"""SQLite store. The only module that runs SQL."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import settings

SCHEMA = Path(__file__).with_name("schema.sql")
RECORD_TABLES = ("parties", "invoices", "ledger_entries", "bank_transactions", "gstr2b_lines", "tax_rates", "filings")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@contextmanager
def connect():
    path = settings.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
    conn.executemany(sql, [[row[c] for c in columns] for row in rows])


def dataset_by_sha(sha256: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE source_sha256 = ?", (sha256,)).fetchone()
    return dict(row) if row else None


def latest_dataset() -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM datasets ORDER BY loaded_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def save_dataset(dataset: dict, records: dict[str, list[dict]]) -> None:
    with connect() as conn:
        insert_rows(conn, "datasets", [dataset])
        for table in RECORD_TABLES:
            insert_rows(conn, table, records[table])


def record_counts(dataset_id: str) -> dict[str, int]:
    with connect() as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE dataset_id = ?", (dataset_id,)).fetchone()[0] for t in RECORD_TABLES}


def periods(dataset_id: str) -> list[str]:
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT period FROM invoices WHERE dataset_id = ? ORDER BY period", (dataset_id,)).fetchall()
    return [r[0] for r in rows]


def create_run(dataset_id: str, period: str) -> str:
    run_id = new_id("run")
    with connect() as conn:
        conn.execute("INSERT INTO runs (id, dataset_id, period, status) VALUES (?, ?, ?, 'queued')", (run_id, dataset_id, period))
    return run_id


def running_run(period: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT id FROM runs WHERE period = ? AND status IN ('queued', 'running')", (period,)).fetchone()
    return row[0] if row else None


def update_run(run_id: str, **fields) -> None:
    with connect() as conn:
        conn.execute(f"UPDATE runs SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", (*fields.values(), run_id))


def fail_stale_runs() -> None:
    """A Run left running by a stopped server can never finish."""
    with connect() as conn:
        conn.execute("UPDATE runs SET status = 'failed', error = 'The server stopped during this Run' WHERE status IN ('queued', 'running')")


def get_run(run_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def latest_run(period: str | None = None) -> dict | None:
    sql = "SELECT * FROM runs WHERE status = 'done'" + (" AND period = ?" if period else "") + " ORDER BY finished_at DESC LIMIT 1"
    with connect() as conn:
        row = conn.execute(sql, (period,) if period else ()).fetchone()
    return dict(row) if row else None


def add_event(run_id: str, stage: str, status: str, message: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO run_events (run_id, stage, status, message, at) VALUES (?, ?, ?, ?, ?)", (run_id, stage, status, message, now()))
        if status == "started":
            conn.execute("UPDATE runs SET stage = ? WHERE id = ?", (stage, run_id))


def events_after(run_id: str, last_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM run_events WHERE run_id = ? AND id > ? ORDER BY id", (run_id, last_id)).fetchall()
    return [dict(r) for r in rows]


def save_results(run_id: str, matches: list[dict], findings: list[dict]) -> None:
    """Write a Run's Matches and Findings, linking each Finding to the Match of its invoice where one exists."""
    match_ids: dict[tuple[str, str], str] = {}
    match_rows = []
    for m in matches:
        match_id = new_id("mat")
        for invoice_id in m["invoice_ids"]:
            match_ids[(m["kind"], invoice_id)] = match_id
        match_rows.append({"id": match_id, "run_id": run_id, "kind": m["kind"], "invoice_id": m["invoice_id"], "right_ids": json.dumps(m["right_ids"]),
                           "layer": m["layer"], "confidence": m["confidence"], "band": m["band"],
                           "reasons_json": json.dumps({"reasons": m["reasons"], "invoice_ids": m["invoice_ids"]})})
    finding_rows = []
    for f in findings:
        tables = {r["table"] for r in f["record_refs"]}
        kind = "supplier_filing" if "gstr2b_lines" in tables else "payment" if "bank_transactions" in tables else "booking" if "ledger_entries" in tables else None
        evidence = {**f["evidence"], "diff": f["diff"], "entity_id": f["entity_id"], "invoice_id": f["invoice_id"]}
        finding_rows.append({
            "id": new_id("fnd"), "run_id": run_id, "finding_type": f["finding_type"], "category": f["category"], "severity": f["severity"],
            "status": "open", "impact_type": f["impact_type"], "impact_paise": f["impact_paise"], "confidence": f["confidence"],
            "deadline": f["deadline"], "party_id": f["party_id"], "title": f["title"], "reason": f["reason"], "rule_ref": f["rule_ref"],
            "what_to_do": f["what_to_do"], "record_refs_json": json.dumps(f["record_refs"]), "evidence_json": json.dumps(evidence),
            "match_id": match_ids.get((kind, f["invoice_id"])) if kind and f["invoice_id"] else None,
        })
    with connect() as conn:
        insert_rows(conn, "matches", match_rows)
        insert_rows(conn, "findings", finding_rows)


def _finding(row: sqlite3.Row) -> dict:
    out = dict(row)
    out["record_refs"] = json.loads(out.pop("record_refs_json"))
    out["evidence"] = json.loads(out.pop("evidence_json"))
    return out


def findings_of(run_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,)).fetchall()
    return [_finding(r) for r in rows]


def get_finding(finding_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    return _finding(row) if row else None


def set_finding_status(finding_id: str, status: str, note: str | None) -> None:
    with connect() as conn:
        conn.execute("UPDATE findings SET status = ?, status_note = ?, status_changed_at = ? WHERE id = ?", (status, note, now(), finding_id))


def _match(row: sqlite3.Row) -> dict:
    out = dict(row)
    packed = json.loads(out.pop("reasons_json"))
    out["right_ids"] = json.loads(out["right_ids"])
    out["reasons"], out["invoice_ids"] = packed["reasons"], packed["invoice_ids"]
    return out


def matches_of(run_id: str, kind: str | None, band: str | None, layer: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    where, args = ["run_id = ?"], [run_id]
    for column, value in (("kind", kind), ("band", band), ("layer", layer)):
        if value:
            where.append(f"{column} = ?")
            args.append(value)
    clause = " AND ".join(where)
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM matches WHERE {clause}", args).fetchone()[0]
        rows = conn.execute(f"SELECT * FROM matches WHERE {clause} ORDER BY (layer = 'one_to_many') DESC, confidence ASC, id LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
    return [_match(r) for r in rows], total


def get_match(match_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    return _match(row) if row else None


def party_names(dataset_id: str) -> dict[str, str]:
    with connect() as conn:
        return dict(conn.execute("SELECT id, name FROM parties WHERE dataset_id = ?", (dataset_id,)).fetchall())


def get_record(dataset_id: str, table: str, record_id: str) -> dict | None:
    if table not in RECORD_TABLES:
        return None
    key = "period" if table == "filings" else "id"
    with connect() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE dataset_id = ? AND {key} = ?", (dataset_id, record_id)).fetchone()
    return dict(row) if row else None


def draft_of(finding_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE finding_id = ?", (finding_id,)).fetchone()
    return dict(row) if row else None


def get_draft(draft_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return dict(row) if row else None


def save_draft(draft: dict) -> None:
    with connect() as conn:
        insert_rows(conn, "drafts", [draft])


def update_draft(draft_id: str, **fields) -> None:
    with connect() as conn:
        conn.execute(f"UPDATE drafts SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", (*fields.values(), draft_id))


def approve_draft(draft_id: str, finding_id: str, note: str | None) -> None:
    """Approving a Draft approves its Finding in the same transaction."""
    stamp = now()
    with connect() as conn:
        conn.execute("UPDATE drafts SET status = 'approved', approved_at = ?, note = ? WHERE id = ?", (stamp, note, draft_id))
        conn.execute("UPDATE findings SET status = 'approved', status_note = ?, status_changed_at = ? WHERE id = ?", (note, stamp, finding_id))
