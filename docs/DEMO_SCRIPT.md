# Demo script

For the prototype video (2 to 2.5 minutes: problem, approach, demo) and, further down, the live presentation. Every number in the lines below was read from the running app on 3 Oct 2026 for the demo month, September 2025. If an engine change moves a number, change it here too.

The spoken lines come to about 360 words, which is about 2 minutes 25 seconds at an even pace. Two cuts are marked if you run long.

## Before you record

1. Build and start the real app, not the dev server: `pnpm --dir frontend build`, then `start.cmd`.
2. Browser at 1920x1080, zoom 100 percent, bookmarks bar hidden, no other tabs.
3. The presenter footer (step 1 of 7 at the bottom) is useful live but covers the bottom of the screen. For the video, remove the line `NEXT_PUBLIC_DEMO=1` from `frontend/.env.local` and build again. Put it back for the live presentation.
4. Open `http://localhost:3000`, press Run again once and let it finish. This warms everything and proves the Run takes about 9 seconds. Then go back to `http://localhost:3000` so the take starts on the landing page.
5. Every Run starts the month fresh with all 129 Findings open, so the Run inside your take resets the two approvals from any earlier take.
6. Drafts for September are cached, so no network is needed and nothing waits on the language model.

## The video, shot by shot

Each shot has two parts. Do is what your hands and the screen do. Say is the exact words, read as written.

### 0:00  The problem

Screen: Landing page, top

Do:

1. Start on the landing page, scrolled to the top. Hold for two seconds.
2. Scroll slowly down to the heading "Four records describe one purchase".
3. Stop with the four record counts and the example on screen.

Say:

> Every month an Indian business has to make four records agree: its invoices, its books, its bank statement, and GSTR-2B, the statement of what its suppliers reported. When they disagree, input tax credit is lost or tax is overpaid, and today that is found late, by hand, in spreadsheets.

### 0:18  The approach

Screen: Landing page, "Seven stages, one month"

Do:

1. Keep scrolling to "Seven stages, one month".
2. Pause with all seven stages on screen.

Say:

> LedgerLens reconciles the month end to end. It prices every mismatch in rupees, shows the evidence, and drafts the fix for you to approve. Code decides every number. The language model only words the explanation.

### 0:30  The Run

Screen: Landing page top, then the Run overlay

Do:

1. Scroll back to the top.
2. Click Run again (it says Load demo company on a fresh install).
3. Do nothing while the feed streams. Let the viewer read the lines.

Say:

> This is one month of books for a demo company: September 2025, the month GST rates changed. These are real records going by: invoice numbers a supplier wrote differently, one payment settling two invoices, and each stage reporting what it found.

### 0:45  The dashboard

Screen: Dashboard

Do:

1. The dashboard opens by itself when the Run ends.
2. Move the pointer along the dark headline band, left to right, as you say each number.
3. Move down to Fix these first, then across to Why credit is at risk.

Say:

> Rupees first. 2.82 lakh rupees of credit is at risk, 3,098 more can be claimed, and Net payable is 34.97 lakh. Below that: what to fix first, and why the credit is at risk.

### 1:00  A Finding, and the approval

Screen: Finding drawer over the dashboard

Do:

1. Click the line with the red dot: "2 invoices this month still use a GST rate that ended on 22 Sep 2025".
2. Point at 28% and 18% in the table, then at Why this was flagged, then at the drafted note.
3. Click Approve draft.
4. Point at the headline band: excess tax now reads Rs 2,681.
5. Close the drawer.

Say:

> Open a Finding. This invoice was charged 28 percent three days after the rate became 18. Here is the record, what it should be, the rule, and a drafted credit note. I approve it, and excess tax drops from 24,117 rupees to 2,681.

### 1:17  A second approval (cut 1 if long)

Screen: Dashboard, then the drawer again

Do:

1. Click See why and fix under Start here in the headline band.
2. Click Approve draft.
3. Close the drawer. The headline now reads Rs 2.23 L.

Say:

> This supplier never reported our invoice, so its credit is at risk. The draft asks them to report it. Approved: credit at risk falls to 2.23 lakh.

### 1:27  Matched, not flagged (cut 2 if long)

Screen: Workbench, Matches tab

Do:

1. Click Workbench in the sidebar.
2. Click Matches.
3. Open a row marked One-to-many.
4. Close it.

Say:

> Not everything odd is wrong. One payment settling two invoices is matched and left alone.

### 1:35  The Supplier ring

Screen: Ring view

Do:

1. Click Ring view in the sidebar.
2. Click the red supplier node, Unity Infra Pvt Ltd. Its panel opens on the right.
3. Scroll down to Follow the money. Pause on the arrows.
4. Scroll on to The ring across the year.

Say:

> The ring view shows who we trade with. This supplier and this customer share one PAN, so one owner sits on both sides. Five lakh rupees went out on 30 September with no invoice and came back on 2 October.

### 1:55  What the month should cost

Screen: Liability

Do:

1. Click Liability in the sidebar.
2. Point at Declared net payable, then at the LedgerLens figure and the gap.

Say:

> The filed return declared 32.15 lakh. LedgerLens shows what the month should cost, tax type by tax type, and the gap.

### 2:03  Proof and the data

Screen: Proof, then Data

Do:

1. Click Proof in the sidebar.
2. Point at the four numbers at the top.
3. Scroll to Every miss, by record.
4. Click Data in the sidebar and scroll to Mistakes planted for LedgerLens to catch.

Say:

> And it is measured, not claimed. The data has planted mistakes and an answer key. On two months the matchers never saw, LedgerLens caught 287 of 288 planted mistakes with 8 false alarms, and every miss is listed by record. The Data page shows exactly what was planted.

### 2:23  Close

Screen: Dashboard

Do:

1. Click Dashboard in the sidebar.
2. Hold on the headline band for three seconds, then stop recording.

Say:

> LedgerLens: what it costs, why, and the fix.

## The words only

The same lines in one block, for rehearsing or recording the voice separately.

**0:00** Every month an Indian business has to make four records agree: its invoices, its books, its bank statement, and GSTR-2B, the statement of what its suppliers reported. When they disagree, input tax credit is lost or tax is overpaid, and today that is found late, by hand, in spreadsheets.

**0:18** LedgerLens reconciles the month end to end. It prices every mismatch in rupees, shows the evidence, and drafts the fix for you to approve. Code decides every number. The language model only words the explanation.

**0:30** This is one month of books for a demo company: September 2025, the month GST rates changed. These are real records going by: invoice numbers a supplier wrote differently, one payment settling two invoices, and each stage reporting what it found.

**0:45** Rupees first. 2.82 lakh rupees of credit is at risk, 3,098 more can be claimed, and Net payable is 34.97 lakh. Below that: what to fix first, and why the credit is at risk.

**1:00** Open a Finding. This invoice was charged 28 percent three days after the rate became 18. Here is the record, what it should be, the rule, and a drafted credit note. I approve it, and excess tax drops from 24,117 rupees to 2,681.

**1:17** This supplier never reported our invoice, so its credit is at risk. The draft asks them to report it. Approved: credit at risk falls to 2.23 lakh.

**1:27** Not everything odd is wrong. One payment settling two invoices is matched and left alone.

**1:35** The ring view shows who we trade with. This supplier and this customer share one PAN, so one owner sits on both sides. Five lakh rupees went out on 30 September with no invoice and came back on 2 October.

**1:55** The filed return declared 32.15 lakh. LedgerLens shows what the month should cost, tax type by tax type, and the gap.

**2:03** And it is measured, not claimed. The data has planted mistakes and an answer key. On two months the matchers never saw, LedgerLens caught 287 of 288 planted mistakes with 8 false alarms, and every miss is listed by record. The Data page shows exactly what was planted.

**2:23** LedgerLens: what it costs, why, and the fix.

## If you run long

Cut in this order. Each cut leaves the story whole.

1. The second approval (1:17). Saves about 10 seconds.
2. The workbench (1:27). Saves about 8 seconds.
3. Shorten the Proof line to: "On two months the matchers never saw, it caught 287 of 288 planted mistakes, and every miss is listed."

## If something goes wrong in the take

- The Run overlay stays up with an error: press Retry in it. If it fails twice, the API window from `start.cmd` shows why.
- A draft says "Written from a template": the cached draft did not match. Run `python -m app.drafts.precache --period 2025-09` from the backend folder (see CLAUDE.md), then record again.
- A number on screen differs from the line you are about to say: say what is on screen. The screen is the truth.

## Where each number comes from

| Line | Number | Screen |
|---|---|---|
| Credit at risk | Rs 2,81,615 (shown as Rs 2.82 L) | Dashboard headline |
| Credit found | Rs 3,098 | Dashboard headline |
| Net payable | Rs 34,96,926 (Rs 34.97 L) | Dashboard headline |
| Open Findings | 129 | Dashboard, Fix these first |
| Rate change invoice | INV-2526-01431, 28 percent on 25 Sep 2025, 18 percent since 22 Sep 2025, Rs 21,436 excess tax | Finding drawer |
| Excess tax after approving it | Rs 24,117 to Rs 2,681; Net payable to Rs 34,75,490 | Dashboard headline |
| Supplier not reporting | VEN041-0020, Titan Logistics Ltd, Rs 58,480 | Start here |
| Credit at risk after approving it | Rs 2,23,135 (Rs 2.23 L) | Dashboard headline |
| Ring | Unity Infra Pvt Ltd (supplier) and Unity Motors Ltd (customer), one PAN; Rs 5,00,000 out on 30 Sep 2025, back on 2 Oct 2025; Rs 53,617 of credit this month | Ring view |
| Filed return | Rs 32,15,311 declared | Liability |
| Catch rate | 287 of 288 planted mistakes (99.7 percent), 8 false alarms, 0 on Benign traps, February and March 2026 | Proof |
| Run time | about 9 seconds | Run overlay |

## The live presentation (10:30 AM)

Same story, with the presenter footer switched on (`NEXT_PUBLIC_DEMO=1`, build again). The footer walks the seven steps in order and names the next one, so you never hunt for a page. Extra beats you have time for live:

- After the Run, press Run log in the header to show the feed again and read two lines aloud.
- On the Ring view, tick "All 120 Parties", search a name, and click an ordinary Party to show its invoices and bank lines.
- On Proof, switch to Whole year and say plainly what changes: more misses, most of them in the unusual-invoice screens, and the whole year is coverage, not an unseen test.
- On Data, browse the bank statement for September and search TXN-002236 to show the round trip is a real row.
- If a judge asks whether the language model decides anything: no. Rules and two trained matchers decide every number. The model words the reason and the draft, and the Proof page compares the matchers with a simple rule score on the same pairs.
