# 05 Build plan

MVP first. Every phase ends in something you can run and show. Commit at the end of every phase with a descriptive message. Run tests and typecheck during each phase, not only at the end. Timeline: the event date is not known yet; ask the user, then add dates here.

## Phases

| Phase | Build | Done when (checkable) | Verify |
|---|---|---|---|
| 1 | ML package steps 1, 1b, 2 to 4 (ML_BUILD.md 11): scaffold, loader, augmentation, normalisers, candidates, features | profile prints facts; augment writes data/derived; tests pass | python -m ledgerlens_ml profile; augment twice gives identical files; pytest ml/tests |
| 2 | ML steps 5 and 6: booking and payment matchers with baseline comparison | cards written with test metrics | train --model booking, --model payment; read cards |
| 3 | Backend scaffold, db.py with schema, records load, POST /api/demo/load, GET /api/health | demo load inserts all Records; row counts equal the workbook plus generated GSTR-2B lines | pytest backend/tests; curl the two endpoints |
| 4 | Engine stage by stage, tests first: tax_rules, duplicates, supplier_filing, one_to_many, rule37, rings, findings, money; run.py with run_events | a September 2025 Run produces Findings including INV-2526-01431 WRONG_TAX_RATE with excess tax about Rs 21,436, and money totals | pytest backend/tests; a script prints the September summary |
| 5 | Remaining API routes and SSE | contract tests for every route in 02-architecture.md | pytest; curl -N the events endpoint during a Run |
| 6 | Frontend scaffold, tokens, shell, lib/api.ts, format.ts, EmptyState, ErrorState | shell renders with sidebar and top bar, health shown | pnpm typecheck, pnpm lint; open in Chrome, screenshot |
| 7 | Start screen and dashboard | Load demo company to dashboard with real numbers, stage animation visible | browser walk; compare with deck/images/mockups/dashboard.png |
| 8 | Finding detail, Drafts (template path first), approve and dismiss | approving the hero Finding updates the dashboard | browser walk including error and empty states |
| 9 | Workbench with One-to-many view | filters work, One-to-many renders | browser walk |
| 10 | Ring view | September ring and cancelled GSTIN visible with reasons | browser walk; compare with deck/images/mockups/supplier_graph.png |
| 11 | Liability and money check against answer_key | computed vs declared gap shown; engine test compares with answer_key | pytest; browser walk |
| 12 | Evaluation (engine plus ML steps 7 to 9) and proof screen | /api/eval returns rows; proof screen renders; ML_REPORT.md written | evaluate; browser walk |
| 13 | Claude Drafts: read claude-api skill, llm.py with cache, precache for 2025-09 | with network off, every September Finding opens a Draft from cache or template | LLM_MODE=cache_only, network off, walk the drawer on 10 Findings |
| 14 | Demo hardening: self-hosted fonts, NEXT_PUBLIC_DEMO next-step control, the 8-step journey | three clean offline runs, zero console errors | full walk with console open; Playwright script of the journey |
| 15 | Quality passes: deslop, then thermo-nuclear review if time allows, then simplify and code-review | review findings resolved or listed | tests and typecheck green |
| 16 to 22 | V2 in order: V1 learned supplier-filing matcher, V2 Isolation Forest, V3 Suppliers, V4 Anomalies, V5 ask in plain English, V6 exports, V7 upload, V8 blocked credit | each has its own check in 01-features.md | per feature |
| 23+ | Stretch: Benford, executable, IRN, GSTR-1 | | |

After phase 7 the demo has a story (load and dashboard). After phase 8 it has the hero moment. After phase 10 it has the second wow moment.

## Task order

Claude Code builds alone, so phases run in sequence. Two safe parallel points if a second session is used: frontend phase 6 can start once phase 3 has fixed the API shapes; the claude-api work in phase 13 can start any time after phase 4.

Integration points where work meets: lib/types.ts must mirror backend/app/schemas.py (regenerate by hand when schemas change, check in the same commit); the frontend label for each finding_type comes from the API (label field), never duplicated in the frontend.

## Decisions made (override if you disagree)

- Demo month September 2025, hero Finding INV-2526-01431 (real dataset row), not the deck's cement example.
- Supplier-filing matching by baseline rule score in MVP; the learned version is V2.
- One worker thread per Run, no queue system.
- No login, one Company.
- SSE for stage progress instead of WebSockets.
- Light theme only, deck tokens.
- Drafts never send email; Approve records the decision and marks the Finding approved.
- Frontend uses client components with fetch for data screens; no server-side data fetching.

## What not to build (yet)

- Login, roles, multiple Companies or periods compared side by side.
- Live GST portal, bank or Tally connectors.
- Sending email or WhatsApp.
- Any ML beyond ML_BUILD.md.
- Dark mode, mobile layout.
- Editing Records in the UI.
- Reopening approved or dismissed Findings.

## Cut features list

Add here anything cut during the build, with one line on why, so it can come back if time allows.
