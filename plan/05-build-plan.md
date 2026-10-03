# 05 Build plan

MVP first. Every phase ends in something you can run and show. Commit at the end of every phase with a descriptive message. Run tests and typecheck during each phase, not only at the end. Timeline: prototype video due 4 Oct 2026, 1:30 AM (2 to 2.5 minutes; script in docs/DEMO_SCRIPT.md, written once the user approves the frontend). Results about 3:00 AM. Final presentation at NSUT Dwarka, 4 Oct 2026, 10:30 AM. Record the video from whatever is working at about midnight; the demo has a story after phase 7, the approve moment after phase 8 and the ring after phase 10.

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
| 12 | Evaluation (engine plus ML steps 8 to 10) and proof screen | /api/eval returns rows; proof screen renders; ML_REPORT.md written | evaluate; browser walk |
| 13 | Claude Drafts: read claude-api skill, llm.py with cache, precache for 2025-09 | with network off, every September Finding opens a Draft from cache or template | LLM_MODE=cache_only, network off, walk the drawer on 10 Findings |
| 14 | Demo hardening: self-hosted fonts, NEXT_PUBLIC_DEMO next-step control, the 8-step journey | three clean offline runs, zero console errors | full walk with console open; Playwright script of the journey |
| 15 | Quality passes: deslop, then thermo-nuclear review if time allows, then simplify and code-review | review findings resolved or listed | tests and typecheck green |
| 16 to 22 | V2 in order: V1 learned supplier-filing matcher, V2 Isolation Forest, V3 Suppliers, V4 Anomalies, V5 ask in plain English, V6 exports, V7 upload, V8 blocked credit | each has its own check in 01-features.md | per feature |
| 23+ | Stretch: Benford, executable, IRN, GSTR-1 | | |

After phase 7 the demo has a story (load and dashboard). After phase 8 it has the hero moment. After phase 10 it has the second wow moment.

## Progress

- Phases 1 to 13 built and tested by the user. Next: the review feedback section below (bugs, redesign, four feature asks), then the demo script, quality passes and deploy.
- Frontend choices made for speed: plain Tailwind components instead of shadcn/ui, an SVG donut and CSS bars instead of Recharts, plain tables instead of TanStack Table. Cytoscape draws the ring view with hand-placed positions. TypeScript is 5.9 (the Next.js scaffold default). The Chrome extension was not connected, so browser checks use Playwright with the installed Chrome.
- Changes from the plan made while building the backend: all routes live in backend/app/routes/api.py; the engine analyses the whole year once (about 20 seconds, cached to backend/cache) and a Run reads its Return period from that, so a Run takes about 5 seconds; anomaly rules live in backend/app/engine/anomalies.py; Drafts use Groq (model openai/gpt-oss-120b), not Claude; GET /api/runs/latest was added so the frontend can find the last Run after a reload.

## Review feedback from the user (3 Oct 2026, first test of the prototype)

The user tested every screen. Overall verdict: it works, but it looks AI-generated and shows too little of the thinking behind it. Do these before the demo script. Answers below were confirmed with the user; nothing here is a guess unless marked.

Status, 3 Oct 2026 late evening: items 1 to 9 are built and pushed. The user picked the bold direction (the one with the dark headline band) after seeing two, then asked for the charts back on the dashboard, which is done. Notes from this work are under "Notes from the review fixes" below. Not yet done: the user's second test of the whole app.

### Bugs

1. The Run overlay names the wrong month. Choosing another Return period shows "Reconciling <the month you were on>" while the stage text is for the chosen month (seen: title December 2025, stage text 2025-10). Cause: lib/run-store.tsx sets period only after the Run ends, and components/Shell.tsx titles the overlay and the select from run.period. Fix: keep a target period in the store from the moment launch or choosePeriod starts, and use it for the overlay title and the select.
2. The red "GST rates changed on 22 Sep 2025" banner: the user asked whether it is right that it shows in January 2026 and never before September. It is right (it lists invoices of that month dated after the change that still use the old rate, for example VEN020-0041 in January 2026). Reword it so a later month does not read like stale news, for example "2 invoices this month still use a rate that ended on 22 Sep 2025".

### Look and feel ("everything looks too much AI")

The user is not sure which direction to take. So: use the impeccable skill, make two quick directions for the landing page and the dashboard only, screenshot both, let the user pick, then apply the chosen one everywhere. Signs of the generated look to remove: grids of icon, title and text cards; many tinted pills and chips; everything boxed in a rounded card; all information at one weight.

3. Landing page: the user's words, "it ain't even a landing page, it's literally a button". Build a complete landing page: what the problem is, how LedgerLens solves it step by step, the features shown with real screens and real numbers from the demo month, the honesty about the data, and the call to action. Keep Load demo company as the main action.
4. Dashboard: too much information at once. Lead with the three rupee numbers, then reveal the rest in an order a first-time viewer can follow (progressive disclosure, fewer boxes, clear reading order).
5. The dark guide bar at the bottom (components/DemoGuide.tsx): keep a guided walk-through but redesign it so it looks intended, not like a generated tooltip.

### Features the user asked for

6. Live feed during a Run (chosen option): while each stage runs, real records stream past, for example "INV-2425-02759 read as INV-2526-02759", "TXN-002349 settles 2 invoices", with counters ticking up, and the feed stays readable after the Run. Needs the backend to send example items per stage (a new SSE event next to stage; the analysis already holds the matches, reasons and Findings to draw from).
7. Ring view, all four: click any Party to see its invoices, payments and Findings for the month with links into the Finding detail; draw the money moving (the Rs 5,00,000 round trip, purchases and sales) as dated, labelled arrows with a short step by step; filters (Suppliers or Customers, all 120 Parties, search, shared bank accounts as well as shared PAN); a timeline of the ring across the year (months traded, credit depending on them).
8. A Data page in the sidebar, all four: what the dataset is and why it is synthetic and why this one was chosen (sheets with row counts); what was planted (every planted error type and Benign trap with counts and a real example row); how GSTR-2B was generated and why each choice was made (ML_BUILD.md 3.5 and data/derived/augment_manifest.json); browse the raw records (invoices, ledger, bank, GSTR-2B for the month, searchable; the SQLite Record tables already hold them).
9. Proof page, all four ("looks good, too good"): the trained matchers against the rule baseline (the cards in ml/artifacts hold both); the misses shown openly (the records missed or wrongly flagged with why, and hard cases caught: typos, part payments); how it was tested (train, validation and test months, what was planted, what counts as a false alarm, limits of synthetic data); a switch between test months and the whole year, and catch rate month by month (engine/evaluate.py already takes a period list).

### Still open from before

- docs/DEMO_SCRIPT.md is written (the user asked for it before the second test). Recheck its numbers if the engine changes.
- Hosted deploy: Dockerfile and render.yaml are untried; needs the user's accounts.
- Quality passes (deslop, simplify, code review) and the answer_key liability test.

## Second round of requests from the user (3 Oct 2026, 11:40 PM)

Asked for after seeing the rebuilt app. Items 1, 2 and 3 are built (README images are in docs/images, taken by a read-only Playwright script at 1440x900; retake them if the look changes). Item 4 is not started. Do not push any of the look changes until the user has seen them locally.

Notes on items 2 and 3: radii come from three sizes in globals.css (r-control 4px, r-surface 6px, r-bar 2px, used as rounded-control, rounded-surface and rounded-bar), so one edit there changes every screen; status dots stay round. Rows that open a Finding use the row-action class with a row-cta label inside: the row tints and the label fills orange on hover. Buttons get the pointer cursor from a rule in globals.css, because Tailwind 4 gives them the default cursor.

Sidebar (asked for after items 2 and 3, because the icon rail with a tinted active box still read as AI-made): a 152px list under the LedgerLens wordmark, a small line icon before each label (the user asked for icons back, but different ones), the current page marked by an orange bar on the left edge. The presenter guide bar in DemoGuide.tsx is offset by the same 152px. At 1440 wide the Start here line on the dashboard now wraps to two lines.

Landing background: frontend/public/landing-bg.png is a ledger paper texture the user generated; it sits behind the problem section only, faded into white above and cream below. frontend/.env.local has NEXT_PUBLIC_DEMO commented out for the video build; put it back and rebuild before the live presentation.

1. README.md for people who are not technical: walk from the problem to the solution and the USP, using sentences from the organisers' problem statement (docs/PROBLEM_STATEMENT.md), with images. The seven capabilities the statement lists should each be answered by what LedgerLens does. It still needs the run steps and the hosted copy section, lower down.
2. Dashboard buttons must look like buttons on hover. Today the action lines (Start here, Rate change), the Findings rows and the text links only underline or tint faintly.
3. Corners are too rounded in many places, which the user reads as the AI look. Radii in use: 9px buttons, 14 to 20px panels and bands, rounded-xl and rounded-full in several places (globals.css and the components).
4. A new visual direction for every UI element, in the user's words: "Light Minimalism + Swiss/Editorial + subtle Glassmorphism + Bento". This replaces parts of the bold direction picked earlier (PRODUCT.md and the notes below describe it). Two tensions to raise once, in a line, and then build what was asked: Bento means content in boxes, which the first review listed as an AI tell ("everything boxed in a rounded card"), and item 3 asks for less rounding, so the boxes need small radii and real hierarchy between them; glass should stay subtle and rare (a header or an overlay), not a default surface. Update PRODUCT.md when the direction settles.

## Notes from the review fixes

- Look: PRODUCT.md is the design brief. Sections sit on a heavy rule (the card class) instead of in boxes, Pill is a dot and a label, PageTitle and Heading in components/ui.tsx carry the type scale. The panel class is for surfaces that float (the Run overlay).
- The landing page uses no pictures. It renders the app's own components (the money strip and cause bar, the Run feed replayed, a Finding that can be approved in the page, the ring diagram, the Proof switch) from frontend/lib/landing-data.json, which frontend/scripts/landing-data.mjs writes from a fresh September Run. Run that script after any engine change that moves the numbers. The user asked for this after seeing screenshots on the first version.
- Dashboard: the top is a title row, a strip of four numbers and two action lines (Start here, Rate change), because the first version read as a landing page hero. Causes are one stacked bar above the Findings list, full width, because side by side the rows looked paired.
- Live feed: backend/app/engine/feed.py picks up to six real lines per stage; they are stored in run_items and streamed as item events next to stage events. Items are ordered by the stage event they follow (after_event), not by time, because timestamps tie when the stage delay is zero. LEDGERLENS_STAGE_DELAY is 0.7 seconds, which gives a Run of about 9 seconds.
- Anything under backend/app/engine is part of the analysis cache key, so every edit there costs a 20 second recompute (python -m app.warm). View code that only reads results lives outside it: backend/app/proof.py and backend/app/ring_view.py.
- Proof: the headline catch rate counts planted mistakes only (287 of 288 on the test months, 8 false alarms). True matches are reported in the matcher section against the rule baseline from the cards. Whole year: 1,567 of 1,586 caught, 34 false alarms, almost all in the anomaly screens.
- Ring view: rings.graph returns every Party; the page draws the 18 largest unless asked for all. No two Parties share a bank account in this data, and the page says so rather than hiding the check.
- The Data page's "why this data" wording is not from a source document; it was written from what the workbook contains. The user should correct it if the real reason for choosing the dataset differs.
- Editing from Git Bash: a path argument starting with a slash is rewritten to a Windows path, and shell heredocs with apostrophes break. Write patch scripts with the Write tool and run them.

## Notes from phases 3 to 13

- Groq key limits (read from the response headers on 3 Oct 2026): 8,000 tokens a minute and 1,000 requests a day for openai/gpt-oss-120b. One Draft costs about 700 tokens, so about 8 Drafts a minute. The precache command waits when the window is empty. When the limit is hit in the app, the Draft falls back to the template and says so.
- backend/cache/drafts holds the cached Drafts (committed, no secrets). A Draft is cached by its prompt, so changing a Finding's title or reason needs a new precache run for that period.
- The whole-year analysis cache (backend/cache/analysis_*.pkl) is keyed by the dataset hash, the two model files and the engine source, so any engine edit makes the next Run recompute for about 20 seconds. Run python -m app.warm from backend after engine changes and before a demo.
- Each Run stores its own Findings, so approvals belong to that Run. Run again gives a fresh month with everything open, which is the reset before recording.
- For September 2025 the gap between the filed return and LedgerLens (Rs 2,81,615) equals ITC at risk exactly, because the return matches the books and only the at-risk credit differs. Good line for the demo.
- The answer_key comparison in phase 11 (engine liability against true_net_tax_liability) is not built. The liability screen compares against the filed return only.
- The ML steps for anomaly model, evaluate report and predict command are not built in ml; anomaly rules and evaluation live in the backend engine.
- The backend must be restarted after code changes (start.cmd does not use reload). Background servers started from a Claude session stop when the session ends.
- Playwright drives the installed Chrome (channel chrome), so no browser download is needed: node frontend/scripts/shots.mjs <folder> for the journey, node frontend/scripts/guide.mjs <folder> for the presenter guide.
- frontend/.env.local (not committed) sets NEXT_PUBLIC_DEMO=1 to show the presenter guide bar. Remove the line and rebuild to hide it.

## Notes from phases 1 and 2 for the phases that follow

- Loading the workbook takes about 7 seconds (openpyxl). Do it once in POST /api/demo/load and keep Records in SQLite; a Run must not reload it. Scoring September 2025 takes about 2 seconds for booking and 3 for payment, so a Run fits the 5 to 10 second budget only if the engine stages stay light.
- The backend gets everything it needs from the package root: load_dataset, resolve_bank, score_pairs, MatchResult, ModelNotTrainedError, is_valid_gstin, MODEL_VERSION. Frames keep workbook column names, with money columns renamed to end in _paise (taxable_value_paise, invoice_total_paise, amount_paise, total_amount_paise). The Dataset also carries manifest (the augmentation manifest) and sha256.
- load_dataset already applies the augmentation: parties has filing_behaviour, gstin_status and cancelled_from, and the ring customer's PAN and GSTIN are rewritten on the party and its invoices. records.py only maps columns and lowercases enums.
- parties.bank_account in schema.sql: every party uses exactly one counterparty_account, so take it from the resolved bank frame (the account of the rows resolved to that party).
- score_pairs returns one MatchResult per invoice. Unmatched results have right_id None and an empty features dict when nothing was assigned. The second invoice of a bundled payment and the second payment of a partial pair come back unmatched or unassigned by design; one_to_many.py picks them up (6 such invoices in September 2025).
- All 60 credit notes are sales credit notes; there are no purchase credit notes. Payment candidates skip credit notes.
- A purchase invoice labelled DUPLICATE_INVOICE has no GSTR-2B line and no MISSING_IN_2B label; the engine must not report it as missing in GSTR-2B.
- Late suppliers: every line sits one Return period after the invoice month and is labelled PERIOD_SHIFT (415 labels in the year, 39 for September invoices). The engine has to decide how loudly to show these; they carry no Rupee impact in the labels.
- Non-filing suppliers with a cancelled GSTIN carry both MISSING_IN_2B and CANCELLED_GSTIN labels on the same invoice. Count the ITC at risk once per invoice in money.py.
- September 2025 augment labels by invoice month: MISSING_IN_2B 11 (Rs 1,35,012 of tax), GSTR2B_VALUE_MISMATCH 5, CANCELLED_GSTIN 3 (supplier VEN-006, cancelled from 2 Sep 2025), RULE_37_UNPAID_180 2, plus 2 GSTR-2B lines missing from the books. Ring: supplier VEN-009 Unity Infra Pvt Ltd and customer CUS-007 Unity Motors Ltd, with the Rs 5,00,000 round trip leaving on 30 Sep 2025 (TXN-002236) and returning on 2 Oct 2025 (TXN-002282).
- The hero invoice INV-2526-01431 matches booking JE-004698 and payment TXN-002447, both at Confidence 1.0.
- Git: data/derived and ml/artifacts are committed and marked in .gitattributes so line endings never change them. Retraining rewrites the artifacts because trained_at changes.
- ML steps 7 to 9 (anomaly rules, evaluate, predict) are not built yet; they belong to phases 4 and 12 here. features.train_aggregates already gives the train-only medians the anomaly rules need.

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
