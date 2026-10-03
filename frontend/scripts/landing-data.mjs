// Writes lib/landing-data.json: the real September 2025 results the landing page shows before any data is loaded.
// Usage: node scripts/landing-data.mjs (needs the backend up). Run it again whenever an engine change moves the numbers.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const api = (process.env.API_URL ?? "http://localhost:8000") + "/api";
const period = "2025-09";
const get = async (path) => (await fetch(api + path)).json();
const post = async (path, body = {}) => (await fetch(api + path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })).json();

// A fresh Run, so nothing is approved and the numbers are the month as found.
const { dataset } = await get("/runs/latest");
const { run_id } = await post("/runs", { dataset_id: dataset.dataset_id, period });
const stages = [];
const items = [];
let kind = "";
for (const line of (await (await fetch(`${api}/runs/${run_id}/events`)).text()).split("\n")) {
  if (line.startsWith("event: ")) kind = line.slice(7).trim();
  else if (line.startsWith("data: ") && kind === "stage") stages.push(JSON.parse(line.slice(6)));
  else if (line.startsWith("data: ") && kind === "item") items.push(JSON.parse(line.slice(6)));
}

const summary = await get(`/runs/${run_id}/summary`);
const liability = await get(`/runs/${run_id}/liability`);
const graph = await get(`/runs/${run_id}/graph`);
const counts = {};
for (const table of ["invoices", "ledger_entries", "bank_transactions", "gstr2b_lines"]) counts[table] = (await get(`/records/${table}?period=${period}&page_size=1`)).total;

const rate = (await get(`/runs/${run_id}/findings?finding_type=WRONG_TAX_RATE&page_size=50`)).items.find((f) => f.title.includes(" since "));
const detail = await get(`/findings/${rate.id}`);
const draft = await post(`/findings/${rate.id}/draft`);

const proof = {};
for (const scope of ["test", "year"]) {
  const report = await get(`/eval?scope=${scope}`);
  const rules = report.rows.filter((r) => r.source === "engine");
  const total = (key) => rules.reduce((sum, r) => sum + r[key], 0);
  proof[scope] = { planted: total("planted"), caught: total("caught"), reported: total("reported"), false_alarms: total("false_alarms"), on_benign_traps: total("on_benign_traps"), months: report.months };
  proof.by_month = report.by_month;
  proof.matchers = report.matchers.map((m) => ({ kind: m.kind, name: m.name, model: m.model, baseline: m.baseline }));
}

const out = {
  period,
  company: dataset.company,
  counts,
  summary: { ...summary, top_findings: summary.top_findings.map(({ label, impact_paise, impact_type, party, record_refs }) => ({ label, impact_paise, impact_type, party: party?.name ?? null, record: record_refs[0]?.id ?? null })) },
  output_paise: liability.by_tax_type.reduce((sum, t) => sum + t.output_paise, 0),
  eligible_paise: liability.by_tax_type.reduce((sum, t) => sum + t.eligible_itc_paise, 0),
  declared: liability.declared,
  run: { stages, items },
  finding: {
    title: detail.title, label: detail.label, impact_paise: detail.impact_paise, impact_type: detail.impact_type, confidence: detail.confidence, party: detail.party?.name ?? null,
    record: detail.record_refs[0]?.id ?? null, invoice_date: detail.evidence.left.fields.invoice_date ?? null, diff: detail.diff.filter((d) => d.differs), rule_ref: detail.rule_ref,
    reason: detail.reason, rule_text: detail.rule_text, what_to_do: detail.what_to_do,
    draft: { recipient: draft.recipient, subject: draft.subject, body: draft.body, source: draft.source },
  },
  ring: { story: graph.stories[0] ?? null, credit_paise: graph.rings.find((r) => r.id === graph.stories[0]?.ring_id)?.itc_at_risk_paise ?? 0 },
  proof,
};
delete out.summary.run_id;
const file = join(dirname(fileURLToPath(import.meta.url)), "..", "lib", "landing-data.json");
writeFileSync(file, JSON.stringify(out, null, 1) + "\n");
console.log("wrote", file, "| at risk", summary.itc_at_risk_paise, "| findings", summary.finding_counts_by_status.open, "| feed lines", items.length);
