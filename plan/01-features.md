# 01 Features

Tags: [MVP] the demo journey breaks without it, [V2] builds if MVP lands early, [STRETCH] never blocking. Ordered by build dependency within each tag. Finding types and enums are fully listed in 03-data-model.md.

## MVP

| # | Feature | Proven by | Depends on |
|---|---|---|---|
| F1 | Dataset load: workbook into typed frames, hash and column checks | ml profile prints ML_BUILD.md 3.3 facts | none |
| F2 | GSTR-2B generation with augment labels (ML_BUILD.md 3.5) | byte-identical rerun; label counts within 1 percent of rates | F1 |
| F3 | Normalisers: invoice ID, party name, paise, dates; counterparty resolution | ML_BUILD.md 4.1 test table passes | F1 |
| F4 | Booking matcher (invoice to Ledger entry) with Confidence, Band, reasons | card metrics meet or report against 5.5 targets | F3 |
| F5 | Payment matcher (invoice to Bank transaction) | same | F3 |
| F6 | One-to-many matches: subset-sum on paise, same Party, 60-day window, at most 15 invoices | bundled and partial Benign traps end matched, not flagged | F5 |
| F7 | Supplier-filing match (purchase invoice to GSTR-2B line) by baseline score, GSTIN exact | MISSING_IN_2B and MISSING_IN_BOOKS catch rate reported | F2, F3 |
| F8 | Tax checks: Effective rate (22 Sep 2025 aware), tax type from place of supply, arithmetic, exempt taxed, taxable at zero, invalid GSTIN | each rule has a unit test with a real dataset row | F1 |
| F9 | Duplicates: invoice, Ledger entry, payment | DUPLICATE_* catch rate reported | F4, F5 |
| F10 | Rule 37 (unpaid over 180 days) and cancelled-GSTIN checks | augment labels caught | F2, F5 |
| F11 | Rule-based Anomalies (ML_BUILD.md 7.1) with reasons | per-rule catch rate | F1 |
| F12 | Supplier ring detection: PAN links, shared bank account, round-trip flows (networkx) | augment PAN_LINKED_RING caught; graph JSON has reasons | F2, F3 |
| F13 | Findings: one table, Rupee impact and type, severity, deadline, rule reference, reason, suggested action | every Finding has impact, reason and evidence refs | F4 to F12 |
| F14 | Money: ITC at risk, ITC found, Net payable by tax type, declared vs computed (tax_filings, answer_key) | engine liability test equals answer_key true_net_tax_liability within Rs 1 on every month where no planted filing error applies | F13 |
| F15 | Run pipeline with streamed stages (SSE) and stored summary | stage events arrive in order in the browser | F13, F14 |
| F16 | API per 02-architecture.md | contract tests pass | F15 |
| F17 | Start screen with Load demo company and stage animation | browser check | F16 |
| F18 | Dashboard: three headline numbers, Match status donut, ITC at risk by cause, top Findings | browser check against deck mockup | F16 |
| F19 | Finding detail: diff view, rule, Confidence, reasons, what to do, Draft, Approve, Edit, Dismiss | approving INV-2526-01431 closes it and updates headline numbers | F16, F21 |
| F20 | Workbench: Findings and Matches table with filters; side panel with diff and One-to-many view | filter by type and Band works; One-to-many renders | F16 |
| F21 | Drafts: Claude with on-disk cache, template fallback, precache command | demo month has a Draft for every Finding with no network | F13 |
| F22 | Supplier ring view: Cytoscape graph plus explanation panel | ring and cancelled GSTIN visible for September 2025 | F12, F16 |
| F23 | Liability screen: Net payable by tax type, declared vs computed gap | numbers equal F14 | F14, F16 |
| F24 | Evaluation: Catch rate and False alarm rate per Finding type on the test split, engine plus ML | eval JSON and report written | F13 |
| F25 | Proof screen | renders F24 | F24 |
| F26 | Demo mode: NEXT_PUBLIC_DEMO=1, next-step control, offline | three clean offline runs of the 8-step journey | all |

## V2

| # | Feature | Proven by |
|---|---|---|
| V1 | Learned supplier-filing matcher (ML_BUILD.md 6) | card beats baseline |
| V2 | Isolation Forest Anomalies (ML_BUILD.md 7.2) | precision target reported |
| V3 | Suppliers screen: scorecard ranked by ITC at risk caused, risk tier rule stated | sorted table, Draft follow-up button |
| V4 | Anomalies screen with reasons | list renders |
| V5 | Ask in plain English: question in, Claude answers only from Run data via tool calls, cached for demo questions | 5 demo questions answered offline |
| V6 | Export: Excel workpaper of Findings and a GSTR-3B draft JSON | files open |
| V7 | Upload own files (same column contract) | a re-saved copy of the workbook loads |
| V8 | Section 17(5) blocked credit check (needs a purpose field in augmentation) | augment labels caught |

## STRETCH

| # | Feature |
|---|---|
| S1 | Benford screen, company level, labelled screening only |
| S2 | Single-file executable for the ML CLI |
| S3 | E-invoice IRN presence check |
| S4 | GSTR-1 side reconciliation |

## Gotchas

- Sales-side GST 2.0 Findings are excess tax, not ITC at risk. The hero Finding is one of these.
- Never fuzzy-match a GSTIN.
- Rule 37 rows are labelled benign in the workbook; see ML_BUILD.md 3.4 before counting false alarms.
