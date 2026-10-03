-- LedgerLens SQLite schema. Keep in exact sync with plan/03-data-model.md.
-- Money is integer paise. Dates are ISO text (YYYY-MM-DD), periods YYYY-MM.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS datasets (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  company_name  TEXT NOT NULL,
  company_gstin TEXT NOT NULL,
  source_sha256 TEXT NOT NULL UNIQUE,
  loaded_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parties (
  id             TEXT NOT NULL,
  dataset_id     TEXT NOT NULL REFERENCES datasets(id),
  name           TEXT NOT NULL,
  party_type     TEXT NOT NULL CHECK (party_type IN ('supplier', 'customer')),
  gstin          TEXT NOT NULL,
  pan            TEXT NOT NULL,
  state_code     INTEGER NOT NULL,
  gstin_status   TEXT NOT NULL DEFAULT 'active' CHECK (gstin_status IN ('active', 'cancelled')),
  cancelled_from TEXT,
  bank_account   TEXT,
  PRIMARY KEY (dataset_id, id)
);

CREATE TABLE IF NOT EXISTS invoices (
  id                  TEXT NOT NULL,
  dataset_id          TEXT NOT NULL REFERENCES datasets(id),
  kind                TEXT NOT NULL CHECK (kind IN ('sales', 'purchase')),
  doc_type            TEXT NOT NULL CHECK (doc_type IN ('invoice', 'credit_note')),
  invoice_date        TEXT NOT NULL,
  period              TEXT NOT NULL,
  party_id            TEXT NOT NULL,
  party_gstin         TEXT NOT NULL,
  place_of_supply     INTEGER NOT NULL,
  hsn                 INTEGER NOT NULL,
  category            TEXT NOT NULL,
  taxable_paise       INTEGER NOT NULL,
  rate_pct            INTEGER NOT NULL,
  cgst_paise          INTEGER NOT NULL,
  sgst_paise          INTEGER NOT NULL,
  igst_paise          INTEGER NOT NULL,
  total_tax_paise     INTEGER NOT NULL,
  total_paise         INTEGER NOT NULL,
  original_invoice_id TEXT,
  PRIMARY KEY (dataset_id, id)
);
CREATE INDEX IF NOT EXISTS ix_invoices_period ON invoices (dataset_id, period, kind);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id              TEXT NOT NULL,
  dataset_id      TEXT NOT NULL REFERENCES datasets(id),
  posting_date    TEXT NOT NULL,
  period          TEXT NOT NULL,
  voucher_type    TEXT NOT NULL CHECK (voucher_type IN ('sales', 'purchase', 'payment', 'receipt', 'credit_note', 'journal', 'tax_payment')),
  account         TEXT NOT NULL,
  party_id        TEXT,
  invoice_ref     TEXT,
  taxable_paise   INTEGER NOT NULL,
  total_tax_paise INTEGER NOT NULL,
  total_paise     INTEGER NOT NULL,
  debit_paise     INTEGER NOT NULL,
  credit_paise    INTEGER NOT NULL,
  utr_ref         TEXT,
  narration       TEXT,
  PRIMARY KEY (dataset_id, id)
);
CREATE INDEX IF NOT EXISTS ix_ledger_period ON ledger_entries (dataset_id, period);

CREATE TABLE IF NOT EXISTS bank_transactions (
  id                TEXT NOT NULL,
  dataset_id        TEXT NOT NULL REFERENCES datasets(id),
  txn_date          TEXT NOT NULL,
  period            TEXT NOT NULL,
  direction         TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
  amount_paise      INTEGER NOT NULL,
  counterparty_name TEXT NOT NULL,
  counterparty_account TEXT,
  resolved_party_id TEXT,
  payment_mode      TEXT NOT NULL,
  utr               TEXT,
  narration         TEXT,
  PRIMARY KEY (dataset_id, id)
);
CREATE INDEX IF NOT EXISTS ix_bank_period ON bank_transactions (dataset_id, period);

CREATE TABLE IF NOT EXISTS gstr2b_lines (
  id                  TEXT NOT NULL,
  dataset_id          TEXT NOT NULL REFERENCES datasets(id),
  supplier_gstin      TEXT NOT NULL,
  trade_name          TEXT NOT NULL,
  invoice_number      TEXT NOT NULL,
  invoice_date        TEXT NOT NULL,
  invoice_value_paise INTEGER NOT NULL,
  place_of_supply     INTEGER NOT NULL,
  rate_pct            INTEGER NOT NULL,
  taxable_paise       INTEGER NOT NULL,
  igst_paise          INTEGER NOT NULL,
  cgst_paise          INTEGER NOT NULL,
  sgst_paise          INTEGER NOT NULL,
  return_period       TEXT NOT NULL,
  itc_available       INTEGER NOT NULL CHECK (itc_available IN (0, 1)),
  PRIMARY KEY (dataset_id, id)
);
CREATE INDEX IF NOT EXISTS ix_2b_period ON gstr2b_lines (dataset_id, return_period);

CREATE TABLE IF NOT EXISTS tax_rates (
  dataset_id     TEXT NOT NULL REFERENCES datasets(id),
  hsn            INTEGER NOT NULL,
  category       TEXT NOT NULL,
  rate_pct       INTEGER NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to   TEXT,
  is_exempt      INTEGER NOT NULL CHECK (is_exempt IN (0, 1)),
  PRIMARY KEY (dataset_id, hsn, effective_from)
);

CREATE TABLE IF NOT EXISTS filings (
  dataset_id        TEXT NOT NULL REFERENCES datasets(id),
  period            TEXT NOT NULL,
  due_date          TEXT NOT NULL,
  filing_date       TEXT,
  output_tax_paise  INTEGER NOT NULL,
  itc_claimed_paise INTEGER NOT NULL,
  net_payable_paise INTEGER NOT NULL,
  true_net_paise    INTEGER NOT NULL,
  PRIMARY KEY (dataset_id, period)
);

CREATE TABLE IF NOT EXISTS runs (
  id           TEXT PRIMARY KEY,
  dataset_id   TEXT NOT NULL REFERENCES datasets(id),
  period       TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
  stage        TEXT CHECK (stage IN ('read', 'clean', 'match', 'check', 'anomalies', 'money', 'explain')),
  started_at   TEXT,
  finished_at  TEXT,
  error        TEXT,
  summary_json TEXT
);

CREATE TABLE IF NOT EXISTS run_events (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id  TEXT NOT NULL REFERENCES runs(id),
  stage   TEXT NOT NULL,
  status  TEXT NOT NULL CHECK (status IN ('started', 'done', 'failed')),
  message TEXT NOT NULL,
  at      TEXT NOT NULL
);

-- Example records shown in the live feed while a stage runs. after_event is the stage event each one follows in the stream.
CREATE TABLE IF NOT EXISTS run_items (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id      TEXT NOT NULL REFERENCES runs(id),
  after_event INTEGER NOT NULL REFERENCES run_events(id),
  stage       TEXT NOT NULL,
  message     TEXT NOT NULL,
  at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
  id           TEXT PRIMARY KEY,
  run_id       TEXT NOT NULL REFERENCES runs(id),
  kind         TEXT NOT NULL CHECK (kind IN ('booking', 'payment', 'supplier_filing')),
  invoice_id   TEXT,
  right_ids    TEXT NOT NULL,
  layer        TEXT NOT NULL CHECK (layer IN ('exact', 'normalised', 'fuzzy', 'model', 'one_to_many')),
  confidence   REAL NOT NULL,
  band         TEXT NOT NULL CHECK (band IN ('auto', 'review', 'unmatched')),
  reasons_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_matches_run ON matches (run_id, kind, band);

CREATE TABLE IF NOT EXISTS findings (
  id                TEXT PRIMARY KEY,
  run_id            TEXT NOT NULL REFERENCES runs(id),
  finding_type      TEXT NOT NULL,
  category          TEXT NOT NULL CHECK (category IN ('matching', 'missing', 'duplicate', 'tax', 'anomaly', 'filing')),
  severity          TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
  status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'approved', 'dismissed')),
  impact_type       TEXT NOT NULL CHECK (impact_type IN ('itc_at_risk', 'itc_found', 'excess_tax', 'short_tax', 'unaccounted_payment', 'open_payable', 'none')),
  impact_paise      INTEGER NOT NULL,
  confidence        REAL NOT NULL,
  deadline          TEXT,
  party_id          TEXT,
  title             TEXT NOT NULL,
  reason            TEXT NOT NULL,
  rule_ref          TEXT,
  what_to_do        TEXT NOT NULL,
  record_refs_json  TEXT NOT NULL,
  evidence_json     TEXT NOT NULL,
  match_id          TEXT REFERENCES matches(id),
  status_note       TEXT,
  status_changed_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_findings_run ON findings (run_id, status, category);

CREATE TABLE IF NOT EXISTS drafts (
  id          TEXT PRIMARY KEY,
  finding_id  TEXT NOT NULL UNIQUE REFERENCES findings(id),
  kind        TEXT NOT NULL CHECK (kind IN ('supplier_email', 'customer_credit_note', 'credit_note_request', 'journal_entry')),
  recipient   TEXT NOT NULL,
  subject     TEXT NOT NULL,
  body        TEXT NOT NULL,
  source      TEXT NOT NULL CHECK (source IN ('llm', 'cache', 'template')),
  status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'dismissed')),
  approved_at TEXT,
  note        TEXT
);

CREATE TABLE IF NOT EXISTS eval_results (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  generated_at     TEXT NOT NULL,
  split            TEXT NOT NULL CHECK (split IN ('test', 'validation', 'all')),
  source           TEXT NOT NULL CHECK (source IN ('engine', 'ml')),
  finding_type     TEXT NOT NULL,
  planted          INTEGER NOT NULL,
  caught           INTEGER NOT NULL,
  false_alarms     INTEGER NOT NULL,
  catch_rate       REAL,
  false_alarm_rate REAL
);
