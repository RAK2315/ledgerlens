"""Every HTTP route. Handlers call the engine and the store, then serialise; no rule or money logic lives here."""
from __future__ import annotations

import asyncio
import json
import threading
from functools import lru_cache

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import db, settings
from ..drafts import llm
from ..engine import analyse, evaluate, findings as views, money, rings, run as runs
from ..engine.labels import META

router = APIRouter(prefix="/api")
_draft_lock = threading.Lock()
LLM_LABEL = {"live": "live", "cache_only": "cache", "template_only": "template"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


class RunRequest(BaseModel):
    dataset_id: str
    period: str


class DraftEdit(BaseModel):
    body: str
    subject: str | None = None


class Note(BaseModel):
    note: str | None = None


def _run(run_id: str) -> dict:
    run = db.get_run(run_id)
    if run is None:
        raise ApiError(404, "run_not_found", f"No Run with id {run_id}")
    return run


def _done_run(run_id: str) -> dict:
    run = _run(run_id)
    if run["status"] != "done":
        raise ApiError(409, "run_not_done", f"Run {run_id} is {run['status']}")
    return run


def _finding(finding_id: str) -> dict:
    finding = db.get_finding(finding_id)
    if finding is None:
        raise ApiError(404, "finding_not_found", f"No Finding with id {finding_id}")
    return finding


def finding_row(f: dict, names: dict[str, str]) -> dict:
    return {
        "id": f["id"], "finding_type": f["finding_type"], "label": META[f["finding_type"]][0], "category": f["category"], "severity": f["severity"],
        "status": f["status"], "impact_type": f["impact_type"], "impact_paise": f["impact_paise"], "confidence": f["confidence"],
        "deadline": f["deadline"], "party": {"id": f["party_id"], "name": names.get(f["party_id"])} if f["party_id"] else None,
        "title": f["title"], "record_refs": f["record_refs"],
    }


def _names(run: dict) -> dict[str, str]:
    return db.party_names(run["dataset_id"])


def _summary(run: dict) -> dict:
    out = runs.summary(run)
    names = _names(run)
    out["top_findings"] = [finding_row(f, names) for f in out["top_findings"]]
    out["run_id"] = run["id"]
    return out


@router.get("/health")
def health() -> dict:
    from ledgerlens_ml import MODEL_VERSION
    return {"status": "ok", "model_version": MODEL_VERSION, "dataset_loaded": db.latest_dataset() is not None, "llm": LLM_LABEL[settings.llm_mode()]}


@router.post("/demo/load")
def demo_load() -> dict:
    return runs.load_demo()


@router.post("/runs")
def create_run(body: RunRequest) -> dict:
    dataset = db.latest_dataset()
    if dataset is None or dataset["id"] != body.dataset_id:
        raise ApiError(404, "dataset_not_found", "Load the demo company first")
    if body.period not in db.periods(body.dataset_id):
        raise ApiError(400, "bad_period", f"No records for the Return period {body.period}")
    try:
        return {"run_id": runs.start(body.dataset_id, body.period), "status": "queued"}
    except runs.RunInProgress:
        raise ApiError(409, "run_in_progress", f"A Run for {body.period} is already running")


@router.get("/runs/latest")
def latest_run(period: str | None = None) -> dict:
    run = db.latest_run(period)
    dataset = db.latest_dataset()
    return {"run": _public_run(run) if run else None,
            "dataset": {"dataset_id": dataset["id"], "company": {"name": dataset["company_name"], "gstin": dataset["company_gstin"]},
                        "periods": db.periods(dataset["id"])} if dataset else None}


def _public_run(run: dict) -> dict:
    return {"run_id": run["id"], "period": run["period"], "status": run["status"], "stage": run["stage"], "started_at": run["started_at"],
            "finished_at": run["finished_at"], "error": run["error"]}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    return _public_run(_run(run_id))


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    _run(run_id)

    async def stream():
        last = 0
        while True:
            for event in db.events_after(run_id, last):
                last = event["id"]
                kind = "failed" if event["status"] == "failed" else "stage"
                data = {"message": event["message"]} if kind == "failed" else {k: event[k] for k in ("stage", "status", "message", "at")}
                yield f"event: {kind}\ndata: {json.dumps(data)}\n\n"
            run = db.get_run(run_id)
            if run["status"] in ("done", "failed") and not db.events_after(run_id, last):
                if run["status"] == "done":
                    yield f"event: done\ndata: {json.dumps({'run_id': run_id})}\n\n"
                return
            await asyncio.sleep(0.15)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/runs/{run_id}/summary")
def run_summary(run_id: str) -> dict:
    out = _summary(_done_run(run_id))
    out.pop("liability")
    return out


@router.get("/runs/{run_id}/liability")
def run_liability(run_id: str) -> dict:
    return runs.summary(_done_run(run_id))["liability"]


@router.get("/runs/{run_id}/findings")
def run_findings(run_id: str, category: str | None = None, finding_type: str | None = None, status: str | None = None,
                 impact_type: str | None = None, party_id: str | None = None, sort: str = "impact",
                 page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)) -> dict:
    run = _done_run(run_id)
    rows = db.findings_of(run_id)
    for field, value in (("category", category), ("finding_type", finding_type), ("status", status), ("impact_type", impact_type), ("party_id", party_id)):
        if value:
            rows = [f for f in rows if f[field] == value]
    if sort == "deadline":
        rows.sort(key=lambda f: (f["deadline"] is None, f["deadline"] or "", money.sort_key(f)))
    else:
        rows.sort(key=money.sort_key)
    names = _names(run)
    start = (page - 1) * page_size
    return {"items": [finding_row(f, names) for f in rows[start:start + page_size]], "total": len(rows)}


def finding_detail(f: dict, names: dict[str, str]) -> dict:
    evidence = f["evidence"]
    return {**finding_row(f, names), "reason": f["reason"], "rule_ref": f["rule_ref"], "rule_text": META[f["finding_type"]][4], "what_to_do": f["what_to_do"],
            "evidence": {"left": evidence["left"], "right": evidence["right"], "expected": evidence["expected"]}, "diff": evidence["diff"],
            "match_id": f["match_id"], "status_note": f["status_note"], "run_id": f["run_id"], "field_labels": views.FIELD_LABELS}


@router.get("/findings/{finding_id}")
def get_finding(finding_id: str) -> dict:
    f = _finding(finding_id)
    return finding_detail(f, _names(_run(f["run_id"])))


def match_row(m: dict) -> dict:
    return {k: m[k] for k in ("id", "kind", "invoice_id", "invoice_ids", "right_ids", "layer", "confidence", "band", "reasons")}


@router.get("/runs/{run_id}/matches")
def run_matches(run_id: str, kind: str | None = None, band: str | None = None, layer: str | None = None,
                page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)) -> dict:
    _done_run(run_id)
    items, total = db.matches_of(run_id, kind, band, layer, page_size, (page - 1) * page_size)
    return {"items": [match_row(m) for m in items], "total": total}


@router.get("/matches/{match_id}")
def get_match(match_id: str) -> dict:
    m = db.get_match(match_id)
    if m is None:
        raise ApiError(404, "match_not_found", f"No Match with id {match_id}")
    b = analyse.books()
    right_view = {"booking": views.ledger_view, "payment": views.bank_view, "supplier_filing": views.line_view}[m["kind"]]
    left = [views.invoice_view(b, i) for i in m["invoice_ids"]]
    right = [right_view(b, r) for r in m["right_ids"]]
    amount = {"booking": "total_amount_paise", "payment": "amount_paise", "supplier_filing": "invoice_value_paise"}[m["kind"]]
    total_left = sum(abs(v["fields"]["invoice_total_paise"]) for v in left)
    total_right = sum(abs(v["fields"][amount]) for v in right)
    diff = views.diff([("invoice_total_paise", total_left, total_right if right else None, None)])
    return {"match": match_row(m), "left": left[0], "left_all": left, "right": right, "diff": diff, "field_labels": views.FIELD_LABELS}


@router.post("/findings/{finding_id}/draft")
def create_draft(finding_id: str) -> dict:
    f = _finding(finding_id)
    names = _names(_run(f["run_id"]))
    # One Draft per Finding even when two requests arrive together.
    with _draft_lock:
        existing = db.draft_of(finding_id)
        if existing:
            return existing
        text = llm.write(f, names.get(f["party_id"]))
        return _save_draft(finding_id, text)


def _save_draft(finding_id: str, text: dict) -> dict:
    draft = {"id": db.new_id("drf"), "finding_id": finding_id, "kind": text["kind"], "recipient": text["recipient"], "subject": text["subject"],
             "body": text["body"], "source": text["source"], "status": "draft", "approved_at": None, "note": None}
    db.save_draft(draft)
    return draft


def _draft(draft_id: str) -> dict:
    draft = db.get_draft(draft_id)
    if draft is None:
        raise ApiError(404, "draft_not_found", f"No Draft with id {draft_id}")
    return draft


@router.patch("/drafts/{draft_id}")
def edit_draft(draft_id: str, body: DraftEdit) -> dict:
    draft = _draft(draft_id)
    if draft["status"] != "draft":
        raise ApiError(409, "draft_closed", f"This Draft is already {draft['status']}")
    fields = {"body": body.body, **({"subject": body.subject} if body.subject else {})}
    db.update_draft(draft_id, **fields)
    return db.get_draft(draft_id)


@router.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: str, body: Note | None = None) -> dict:
    draft = _draft(draft_id)
    f = _finding(draft["finding_id"])
    if f["status"] != "open":
        raise ApiError(409, "finding_closed", f"This Finding is already {f['status']}")
    db.approve_draft(draft_id, f["id"], body.note if body else None)
    run = _run(f["run_id"])
    out = _summary(run)
    out.pop("liability")
    return {"draft": db.get_draft(draft_id), "finding": finding_row(_finding(f["id"]), _names(run)), "summary": out}


@router.post("/findings/{finding_id}/dismiss")
def dismiss_finding(finding_id: str, body: Note) -> dict:
    f = _finding(finding_id)
    if f["status"] != "open":
        raise ApiError(409, "finding_closed", f"This Finding is already {f['status']}")
    if not (body.note or "").strip():
        raise ApiError(400, "note_required", "Say why this Finding is dismissed")
    db.set_finding_status(finding_id, "dismissed", body.note)
    draft = db.draft_of(finding_id)
    if draft and draft["status"] == "draft":
        db.update_draft(draft["id"], status="dismissed")
    run = _run(f["run_id"])
    out = _summary(run)
    out.pop("liability")
    return {"finding": finding_row(_finding(finding_id), _names(run)), "summary": out}


@router.get("/runs/{run_id}/graph")
def run_graph(run_id: str) -> dict:
    run = _done_run(run_id)
    result, _ = analyse.analysis()
    return rings.graph(analyse.books(), run["period"], [f for f in result.findings if f["period"] == run["period"]])


@lru_cache(maxsize=1)
def _eval_rows() -> tuple[list[dict], str]:
    from ledgerlens_ml import TEST_MONTHS
    result, _ = analyse.analysis()
    rows = [{**r, "label": META[r["finding_type"]][0], "source": "engine"} for r in evaluate.evaluate(analyse.dataset(), result.findings, TEST_MONTHS)
            if r["planted"] or r["reported"]]
    for kind, name in (("booking", "Invoice to ledger match"), ("payment", "Invoice to bank match")):
        card = json.loads((settings.REPO_ROOT / "ml" / "artifacts" / f"matcher_{kind}.card.json").read_text(encoding="utf-8"))
        pair = card["test"]["pair"]
        auto = round(pair["positives"] * pair["recall"])
        wrong = round(auto / pair["precision"] - auto) if pair["precision"] else 0
        rows.append({"finding_type": f"MATCH_{kind.upper()}", "label": name, "planted": pair["positives"], "caught": auto, "reported": auto + wrong,
                     "false_alarms": wrong, "on_benign_traps": 0, "catch_rate": pair["recall"], "false_alarm_rate": pair["false_auto_rate"], "source": "ml"})
    return rows, db.now()


@router.get("/eval")
def get_eval() -> dict:
    rows, generated_at = _eval_rows()
    return {"split": "test", "rows": rows, "generated_at": generated_at}
