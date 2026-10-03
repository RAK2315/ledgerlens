# Earlier spec: parts that still apply

The user wrote a first spec in Claude web before this blueprint. Where it conflicts with CLAUDE.md, CONTEXT.md, ML_BUILD.md or plan/00-overview.md, those files win. Superseded items are listed at the end so nobody re-adds them.

## USP priority (from the earlier spec, still valid)

1. Rupee impact on every Finding, both ITC at risk and ITC found. Never cut.
2. Explainable diff view: Records side by side, differing fields highlighted, Confidence with stated reasons. Never cut.
3. Measured accuracy against Ground truth, per Finding type. Never cut.
4. One-to-many matching (split and bundled payments). Core.
5. Supplier scorecard ranked by ITC at risk caused. Core (V2 in the scope cut line for the ranking screen; the numbers come free with Findings).
6. Drafted Supplier email and correcting Ledger entry. Core, template fallback.
7. Benford first-digit screen. Stretch.
8. Rate-change detection. Promoted to MVP: the 22 Sep 2025 change is verified.

## API sketch (refine in plan/02-architecture.md)

| Method | Path | Returns |
|---|---|---|
| POST | /api/demo/load | loads the demo dataset, returns dataset id |
| POST | /api/run/{dataset_id}?period=YYYY-MM | starts a Run, returns run id |
| GET | /api/run/{run_id}/events | server-sent events: stage progress for the animation |
| GET | /api/summary/{run_id} | headline numbers, Match status counts, ITC at risk by cause |
| GET | /api/findings/{run_id} | paginated Findings, filters: type, Party, Band, impact type |
| GET | /api/findings/{run_id}/{finding_id} | one Finding with evidence Records and field diff |
| GET | /api/match/{run_id}/{match_id} | both sides, field diff, Confidence, reasons |
| GET | /api/liability/{run_id} | Net payable by tax type, declared vs computed |
| GET | /api/suppliers/{run_id} | scorecard rows |
| GET | /api/graph/{run_id} | Supplier ring nodes and edges with reasons |
| GET | /api/anomalies/{run_id} | Anomalies with reasons (plus Benford data, stretch) |
| POST | /api/drafts/{finding_id} | returns the cached or template Draft |
| POST | /api/drafts/{draft_id}/approve | records Approval, closes the Finding, returns updated summary |
| GET | /api/eval | Catch rate and False alarm rate per Finding type |
| POST | /api/upload | V2: your own files |

Pydantic models for every response. CORS on for the frontend origin.

## Screens (map to plan/04-design-system.md)

1. Start: Load demo company button, file drop zones (V2), stage animation while the Run streams.
2. Dashboard: three headline numbers, Match status donut, ITC at risk by cause, top Findings.
3. Workbench: filterable Findings and Matches table (TanStack Table); row opens a side panel with the diff view, Confidence bar, reasons, approve or dismiss for review-Band items, One-to-many view inside the panel.
4. Finding detail and Draft: the issue drawer from the deck, with Approve and send, Edit draft, Dismiss with note.
5. Supplier ring view: Cytoscape graph plus explanation panel.
6. Liability: Net payable by tax type, waterfall from output tax to net payable, with a "simplified" badge where the ITC set-off order is simplified.
7. Suppliers: scorecard (V2 ranking).
8. Anomalies: list with reasons; Benford chart (stretch) labelled screening only.
9. Proof: Catch rate and False alarm rate per Finding type.

Demo mode: NEXT_PUBLIC_DEMO=1 uses the seeded dataset and cached Drafts, and shows a small next-step control so the presenter can jump screens if anything fails.

## AI layer

- Env vars: ANTHROPIC_API_KEY, LLM_MODEL (default claude-sonnet-5-5). Read the claude-api skill before writing this code.
- Every response cached on disk keyed by a hash of the prompt; template fallback when no key, no cache hit, or an error.
- A precache command fills the cache for every demo-month Finding before the event.
- The model receives only the evidence JSON of one Finding and returns a reason and a Draft. It never produces a number.

## Research still to verify (docs/RESEARCH.md, with source URL and access date)

GSTR-2B field names (official schema), Section 16(2) and 16(4) wording, Rule 37 wording, Section 17(5) categories, interest rate on wrongly availed ITC and its section, ITC set-off order across IGST, CGST and SGST, e-invoicing threshold, Benford MAD thresholds, competitor features (only from their own pages). Facts already sourced are in deck/NOTES.md.

## Superseded, do not re-add

- Dark-first UI: replaced by the light theme from the deck tokens.
- Generating the whole dataset from scratch with Faker: replaced by the provided workbook plus GSTR-2B augmentation (ML_BUILD.md 3).
- The M-numbered commit message format: not adopted; write normal descriptive commits per CLAUDE.md. Subagents: only when the user asks for them.
