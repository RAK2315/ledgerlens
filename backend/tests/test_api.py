import json

STAGES = ["read", "clean", "match", "check", "anomalies", "money", "explain"]
FINDING_ROW = {"id", "finding_type", "label", "category", "severity", "status", "impact_type", "impact_paise", "confidence", "deadline", "party", "title", "record_refs"}
SUMMARY = {"period", "itc_at_risk_paise", "itc_found_paise", "excess_tax_paise", "net_payable_paise", "match_counts", "finding_counts_by_category",
           "itc_at_risk_by_cause", "top_findings"}


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "model_version", "dataset_loaded", "llm"}
    assert body["llm"] in ("live", "cache", "template")


def test_demo_load_inserts_every_record_once(client, loaded):
    from app.engine import analyse
    ds = analyse.dataset()
    assert loaded["company"] == {"name": "Sharma Traders Pvt Ltd", "gstin": "07AAACS1234F1ZU"}
    assert loaded["counts"] == {"parties": len(ds.parties), "invoices": len(ds.invoices), "ledger_entries": len(ds.ledger),
                                "bank_transactions": len(ds.bank), "gstr2b_lines": len(ds.gstr2b), "tax_rates": len(ds.tax_rates), "filings": len(ds.filings)}
    assert loaded["periods"][0] == "2025-04" and "2025-09" in loaded["periods"]
    again = client.post("/api/demo/load").json()
    assert again["dataset_id"] == loaded["dataset_id"] and again["counts"] == loaded["counts"]
    assert client.get("/api/health").json()["dataset_loaded"] is True


def _stream(client, run_id):
    events = []
    with client.stream("GET", f"/api/runs/{run_id}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        kind = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                events.append((kind, json.loads(line[6:])))
    return events


def test_run_finishes_and_streams_stages_in_order(client, run_id):
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "done", run
    assert set(run) >= {"run_id", "period", "status", "stage", "started_at", "finished_at"}
    events = _stream(client, run_id)
    assert events[-1] == ("done", {"run_id": run_id})
    stages = [(e["stage"], e["status"]) for kind, e in events if kind == "stage"]
    assert stages == [(s, status) for s in STAGES for status in ("started", "done")]
    assert all(set(e) == {"stage", "status", "message", "at"} for kind, e in events if kind == "stage")


def test_run_streams_real_records_inside_their_stage(client, run_id):
    events = _stream(client, run_id)
    items = [e for kind, e in events if kind == "item"]
    assert items and all(set(e) == {"stage", "message", "at"} and e["message"] for e in items)
    assert {e["stage"] for e in items} >= {"read", "match"}
    open_stage = None
    for kind, e in events:
        if kind == "stage":
            open_stage = e["stage"] if e["status"] == "started" else None
        elif kind == "item":
            assert e["stage"] == open_stage
    known = {row["id"] for table in ("invoices", "bank_transactions") for row in client.get(f"/api/records/{table}", params={"period": "2025-09", "page_size": 500}).json()["items"]}
    read = [e["message"] for e in items if e["stage"] == "read"]
    assert any(message.split()[0] in known for message in read)


def test_run_errors(client, loaded):
    assert client.post("/api/runs", json={"dataset_id": "ds_nope", "period": "2025-09"}).status_code == 404
    bad = client.post("/api/runs", json={"dataset_id": loaded["dataset_id"], "period": "1999-01"})
    assert bad.status_code == 400 and set(bad.json()["error"]) == {"code", "message"}
    assert client.get("/api/runs/run_missing").status_code == 404
    assert client.post("/api/runs", json={"period": "2025-09"}).status_code == 400


def test_summary_and_findings(client, run_id):
    summary = client.get(f"/api/runs/{run_id}/summary").json()
    assert SUMMARY <= set(summary)
    assert set(summary["match_counts"]) >= {"auto", "review", "unmatched", "one_to_many"}
    assert all(isinstance(summary[k], int) for k in ("itc_at_risk_paise", "itc_found_paise", "excess_tax_paise", "net_payable_paise"))
    listing = client.get(f"/api/runs/{run_id}/findings", params={"page_size": 500}).json()
    assert listing["total"] == sum(summary["finding_counts_by_category"].values()) > 0
    assert all(set(item) == FINDING_ROW for item in listing["items"])
    tax = client.get(f"/api/runs/{run_id}/findings", params={"category": "tax", "page_size": 5}).json()
    assert all(item["category"] == "tax" for item in tax["items"]) and len(tax["items"]) <= 5
    assert [f["id"] for f in summary["top_findings"]] == [f["id"] for f in listing["items"][:len(summary["top_findings"])]]


def test_finding_detail_draft_and_approve(client, run_id):
    before = client.get(f"/api/runs/{run_id}/summary").json()
    target = next(f for f in client.get(f"/api/runs/{run_id}/findings", params={"impact_type": "itc_at_risk"}).json()["items"])
    detail = client.get(f"/api/findings/{target['id']}").json()
    assert {"reason", "rule_ref", "rule_text", "what_to_do", "evidence", "diff", "match_id"} <= set(detail)
    assert set(detail["evidence"]) == {"left", "right", "expected"} and set(detail["evidence"]["left"]) == {"table", "id", "fields"}

    draft = client.post(f"/api/findings/{target['id']}/draft").json()
    assert set(draft) >= {"id", "finding_id", "kind", "recipient", "subject", "body", "source", "status"}
    assert draft["source"] == "template" and draft["status"] == "draft"
    assert client.post(f"/api/findings/{target['id']}/draft").json()["id"] == draft["id"]
    edited = client.patch(f"/api/drafts/{draft['id']}", json={"body": "Edited body"}).json()
    assert edited["body"] == "Edited body"

    approved = client.post(f"/api/drafts/{draft['id']}/approve", json={}).json()
    assert approved["draft"]["status"] == "approved" and approved["finding"]["status"] == "approved"
    assert approved["summary"]["itc_at_risk_paise"] < before["itc_at_risk_paise"]
    assert client.post(f"/api/drafts/{draft['id']}/approve", json={}).status_code == 409
    assert client.patch(f"/api/drafts/{draft['id']}", json={"body": "x"}).status_code == 409


def test_dismiss_needs_a_note(client, run_id):
    target = client.get(f"/api/runs/{run_id}/findings", params={"status": "open"}).json()["items"][0]
    assert client.post(f"/api/findings/{target['id']}/dismiss", json={"note": " "}).status_code == 400
    done = client.post(f"/api/findings/{target['id']}/dismiss", json={"note": "Checked with the Supplier"}).json()
    assert done["finding"]["status"] == "dismissed" and "summary" in done
    assert client.post(f"/api/findings/{target['id']}/dismiss", json={"note": "again"}).status_code == 409
    assert client.get("/api/findings/fnd_missing").status_code == 404


def test_matches_liability_graph_and_eval(client, run_id):
    matches = client.get(f"/api/runs/{run_id}/matches", params={"kind": "payment", "band": "auto"}).json()
    assert matches["total"] > 0
    assert all(set(m) == {"id", "kind", "invoice_id", "invoice_ids", "right_ids", "layer", "confidence", "band", "reasons"} for m in matches["items"])
    matched = next(m for m in matches["items"] if m["right_ids"])
    detail = client.get(f"/api/matches/{matched['id']}").json()
    assert set(detail) >= {"match", "left", "right", "diff"} and len(detail["right"]) == len(matched["right_ids"])

    liability = client.get(f"/api/runs/{run_id}/liability").json()
    assert [row["tax_type"] for row in liability["by_tax_type"]] == ["igst", "cgst", "sgst"]
    assert all(row["net_paise"] == row["output_paise"] - row["eligible_itc_paise"] for row in liability["by_tax_type"])
    assert set(liability["declared"]) == {"output_paise", "itc_paise", "net_paise", "filed_on", "due_on"} and liability["simplified_setoff"] is True

    graph = client.get(f"/api/runs/{run_id}/graph").json()
    assert set(graph) == {"nodes", "edges", "rings"} and graph["nodes"][0]["kind"] == "company"
    assert {e["kind"] for e in graph["edges"]} <= {"trade", "same_pan", "same_bank", "same_address"}

    report = client.get("/api/eval").json()
    assert report["split"] == "test" and {"finding_type", "planted", "caught", "false_alarms", "catch_rate", "false_alarm_rate", "source"} <= set(report["rows"][0])
    assert {row["source"] for row in report["rows"]} == {"engine", "ml"}
