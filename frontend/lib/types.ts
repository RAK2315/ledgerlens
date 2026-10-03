// Mirrors the shapes returned by backend/app/routes/api.py. Change both in the same commit.

export type Company = { name: string; gstin: string };
export type DatasetInfo = { dataset_id: string; company: Company; periods: string[] };
export type Health = { status: string; model_version: string; dataset_loaded: boolean; llm: "live" | "cache" | "template" };
export type RunInfo = { run_id: string; period: string; status: "queued" | "running" | "done" | "failed"; stage: string | null; error?: string | null };
export type StageEvent = { stage: string; status: "started" | "done"; message: string; at: string };
export type FeedItem = { stage: string; message: string; at: string };

export type ImpactType = "itc_at_risk" | "itc_found" | "excess_tax" | "short_tax" | "unaccounted_payment" | "open_payable" | "none";
export type Category = "matching" | "missing" | "duplicate" | "tax" | "anomaly" | "filing";
export type RecordRef = { table: string; id: string };

export type FindingRow = {
  id: string;
  finding_type: string;
  label: string;
  category: Category;
  severity: "critical" | "high" | "medium" | "low";
  status: "open" | "approved" | "dismissed";
  impact_type: ImpactType;
  impact_paise: number;
  confidence: number;
  deadline: string | null;
  party: { id: string; name: string | null } | null;
  title: string;
  record_refs: RecordRef[];
};

export type FieldValue = string | number | boolean | null;
export type RecordView = { table: string; id: string; fields: Record<string, FieldValue> };
export type FieldDiff = { field: string; label: string; left: FieldValue; right: FieldValue; expected: FieldValue; differs: boolean };

export type FindingDetail = FindingRow & {
  reason: string;
  rule_ref: string | null;
  rule_text: string;
  what_to_do: string;
  evidence: { left: RecordView; right: RecordView | null; expected: Record<string, FieldValue> | null };
  diff: FieldDiff[];
  match_id: string | null;
  status_note: string | null;
  run_id: string;
  field_labels: Record<string, string>;
};

export type Summary = {
  run_id: string;
  period: string;
  itc_at_risk_paise: number;
  itc_found_paise: number;
  excess_tax_paise: number;
  short_tax_paise: number;
  net_payable_paise: number;
  invoice_count: number;
  match_counts: { auto: number; review: number; unmatched: number; one_to_many: number; open: number };
  finding_counts_by_category: Partial<Record<Category, number>>;
  finding_counts_by_status: Partial<Record<"open" | "approved" | "dismissed", number>>;
  itc_at_risk_by_cause: { finding_type: string; label: string; paise: number }[];
  top_findings: FindingRow[];
};

export type MatchRow = {
  id: string;
  kind: "booking" | "payment" | "supplier_filing";
  invoice_id: string;
  invoice_ids: string[];
  right_ids: string[];
  layer: "exact" | "normalised" | "fuzzy" | "model" | "one_to_many";
  confidence: number;
  band: "auto" | "review" | "unmatched";
  reasons: string[];
};
export type MatchDetail = { match: MatchRow; left: RecordView; left_all: RecordView[]; right: RecordView[]; diff: FieldDiff[]; field_labels: Record<string, string> };

export type Draft = {
  id: string;
  finding_id: string;
  kind: string;
  recipient: string;
  subject: string;
  body: string;
  source: "llm" | "cache" | "template";
  status: "draft" | "approved" | "dismissed";
};

export type Liability = {
  by_tax_type: { tax_type: "igst" | "cgst" | "sgst"; output_paise: number; eligible_itc_paise: number; net_paise: number }[];
  declared: { output_paise: number; itc_paise: number; net_paise: number; filed_on: string; due_on: string } | null;
  gap_paise: number | null;
  simplified_setoff: boolean;
};

export type GraphNode = { id: string; label: string; kind: "company" | "supplier" | "customer"; risk: "clean" | "ring" | "cancelled" };
export type GraphEdge = { source: string; target: string; kind: "trade" | "same_pan" | "same_bank" | "same_address"; label: string };
export type Ring = { id: string; members: string[]; reason: string; itc_at_risk_paise: number; invoice_count: number };
export type Graph = { nodes: GraphNode[]; edges: GraphEdge[]; rings: Ring[] };

export type EvalRow = {
  finding_type: string;
  label: string;
  planted: number;
  caught: number;
  reported: number;
  false_alarms: number;
  on_benign_traps: number;
  catch_rate: number | null;
  false_alarm_rate: number | null;
  source: "engine" | "ml";
};
export type PlantedType = {
  issue_type: string;
  label: string;
  category: string;
  source: "workbook" | "augment";
  benign: boolean;
  count: number;
  example: { entity_type: string; entity_id: string; field: string | null; expected: string | null; recorded: string | null; description: string | null; impact_paise: number };
};
export type DatasetOverview = {
  sha256: string;
  sheets: { name: string; rows: number }[];
  workbook_labels: number;
  planted: PlantedType[];
  gstr2b: {
    seed: number;
    rates: { filing_behaviour: Record<string, number>; id_variant: number; value_mismatch: number; date_shift: number; extra_lines: number };
    counts: { id_variants: number; value_mismatches: number; date_shifts: number; purchase_invoices: number; gstr2b_lines: number; extra_lines: number; labels: Record<string, number> };
    behaviours: Record<string, number>;
  };
};
export type RecordTable = "invoices" | "ledger_entries" | "bank_transactions" | "gstr2b_lines";
export type RecordPage = { items: Record<string, FieldValue>[]; total: number };
export type EvalReport = { split: string; rows: EvalRow[]; generated_at: string };
