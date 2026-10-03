# Demo script

For the prototype video (2 to 2.5 minutes: problem, approach, demo) and, further down, the live presentation. Every number in the lines below was read from the running app on 3 Oct 2026 for the demo month, September 2025. If an engine change moves a number, change it here too.

The spoken lines come to 395 words over 2:29. The words are meant to fill each shot, so you talk while you click.

## Before you record

1. Build and start the real app, not the dev server: `pnpm --dir frontend build`, then `start.cmd`.
2. Browser at 1920x1080, zoom 100 percent, bookmarks bar hidden, no other tabs.
3. The presenter footer (step 1 of 7 at the bottom) is useful live but covers the bottom of the screen. For the video, remove the line `NEXT_PUBLIC_DEMO=1` from `frontend/.env.local` and build again. Put it back for the live presentation.
4. Open `http://localhost:3000`, press Run again once and let it finish. This warms everything and proves the Run takes about 9 seconds. Then go back to `http://localhost:3000` so the take starts on the landing page.
5. Every Run starts the month fresh with all 129 Findings open, so the Run inside your take resets the two approvals from any earlier take.
6. Drafts for September are cached, so no network is needed and nothing waits on the language model.

## The video, shot by shot

Each shot has a short Do list and the exact words to Say. The words are written to fill the shot: start speaking as the shot starts and do the actions while you talk, so there is no silence.

In all: 395 words over 2:29, which is a brisk but clear pace (about 160 words a minute). Rehearse once with a timer. If you speak slower, use the cuts below rather than rushing.

### 0:00 to 0:23  The problem

Screen: Landing page, top

Do:

1. Start at the top of the landing page.
2. Scroll slowly to "Four records describe one purchase" and stop there.

Say (61 words):

> Every month an Indian business has to make four records agree: its invoices, its books, its bank statement, and GSTR-2B, the statement of what its suppliers reported. When they disagree, it loses input tax credit, the tax paid on purchases that it can deduct from what it owes, or it overpays tax. Today that is found late, by hand, in spreadsheets.

### 0:23 to 0:37  The approach

Screen: Landing page, "Seven stages, one month"

Do:

1. Scroll on to "Seven stages, one month" and stop. The feed on the right replays by itself; let it run.

Say (35 words):

> LedgerLens reconciles the month end to end. It prices every mismatch in rupees, shows the evidence, and drafts the fix for you to approve. Code decides every number. The language model only words the explanation.

### 0:37 to 0:52  The Run

Screen: Landing page top, then the Run overlay

Do:

1. Scroll to the top and click Run again (Load demo company on a fresh install).
2. Hands off while the feed streams.

Say (40 words):

> This is one month of books for a demo company: September 2025, the month GST rates changed. What you see going by are real records: invoice numbers a supplier wrote in its own style, and one payment settling two invoices.

### 0:52 to 1:08  The dashboard

Screen: Dashboard

Do:

1. Move the pointer across the four numbers as you name them.
2. Scroll slowly down through the page to the charts.

Say (40 words):

> Rupees first. 2.82 lakh rupees of credit is at risk, 3,098 more can be claimed, and Net payable, the tax to pay this month, is 34.97 lakh. Below that: why the credit is at risk and what to fix first.

### 1:08 to 1:32  A Finding, and the approval

Screen: Finding drawer over the dashboard

Do:

1. Scroll to the top and click the Rate change line.
2. Point at 28% and 18%, then at the drafted note.
3. Click Approve draft, then close the drawer.

Say (63 words):

> Open a Finding. This invoice was charged 28 percent, three days after the rate for that product became 18. On the left is what the invoice says, on the right what it should be, then the rule in plain words. Below it is a credit note, already drafted. I approve it, and excess tax on the dashboard drops from 24,117 rupees to 2,681.

### 1:32 to 1:56  The Supplier ring

Screen: Ring view

Do:

1. Click Ring view, then click the red supplier node.
2. Scroll to Follow the money, pause, then on to The ring across the year.

Say (70 words):

> The ring view shows everyone we trade with. Two of them are red. This supplier and this customer share one PAN, so one owner sits on both sides of our books. Follow the money: we buy from one, sell to the other, and on 30 September five lakh rupees went out with no invoice and came back on 2 October. Across the year, 8.26 lakh of credit depended on them.

### 1:56 to 2:04  What the month should cost

Screen: Liability

Do:

1. Click Liability.

Say (21 words):

> The filed return declared 32.15 lakh. LedgerLens shows what the month should cost, tax type by tax type, and the gap.

### 2:04 to 2:24  Proof and the data

Screen: Proof, then Data

Do:

1. Click Proof and scroll to Every miss, by record.
2. Click Data and scroll to the planted mistakes.

Say (57 words):

> And it is measured, not claimed. The data has mistakes planted on purpose and an answer key. On two months the matchers never saw, LedgerLens caught 287 of 288 planted mistakes, with 8 false alarms, and every miss is listed by record. The Data page shows exactly what was planted, and lets you check any record yourself.

### 2:24 to 2:29  Close

Screen: Dashboard

Do:

1. Click Dashboard and hold.

Say (8 words):

> LedgerLens: what it costs, why, and the fix.

## The words only

The same lines in one block, for rehearsing or for recording the voice first and the screen to match.

**0:00** Every month an Indian business has to make four records agree: its invoices, its books, its bank statement, and GSTR-2B, the statement of what its suppliers reported. When they disagree, it loses input tax credit, the tax paid on purchases that it can deduct from what it owes, or it overpays tax. Today that is found late, by hand, in spreadsheets.

**0:23** LedgerLens reconciles the month end to end. It prices every mismatch in rupees, shows the evidence, and drafts the fix for you to approve. Code decides every number. The language model only words the explanation.

**0:37** This is one month of books for a demo company: September 2025, the month GST rates changed. What you see going by are real records: invoice numbers a supplier wrote in its own style, and one payment settling two invoices.

**0:52** Rupees first. 2.82 lakh rupees of credit is at risk, 3,098 more can be claimed, and Net payable, the tax to pay this month, is 34.97 lakh. Below that: why the credit is at risk and what to fix first.

**1:08** Open a Finding. This invoice was charged 28 percent, three days after the rate for that product became 18. On the left is what the invoice says, on the right what it should be, then the rule in plain words. Below it is a credit note, already drafted. I approve it, and excess tax on the dashboard drops from 24,117 rupees to 2,681.

**1:32** The ring view shows everyone we trade with. Two of them are red. This supplier and this customer share one PAN, so one owner sits on both sides of our books. Follow the money: we buy from one, sell to the other, and on 30 September five lakh rupees went out with no invoice and came back on 2 October. Across the year, 8.26 lakh of credit depended on them.

**1:56** The filed return declared 32.15 lakh. LedgerLens shows what the month should cost, tax type by tax type, and the gap.

**2:04** And it is measured, not claimed. The data has mistakes planted on purpose and an answer key. On two months the matchers never saw, LedgerLens caught 287 of 288 planted mistakes, with 8 false alarms, and every miss is listed by record. The Data page shows exactly what was planted, and lets you check any record yourself.

**2:24** LedgerLens: what it costs, why, and the fix.

## If you run long

Cut in this order. Each cut leaves the story whole.

1. In the dashboard shot, stop after "is 34.97 lakh." Saves about 5 seconds.
2. In the ring shot, drop the last sentence about the year. Saves about 5 seconds.
3. In the proof shot, drop the last sentence about the Data page and do not open Data. Saves about 7 seconds.

## If you have time to spare

Two short beats that fit between the Finding and the ring. Each adds about 10 seconds.

- A second approval. Do: click the Start here line, click Approve draft, close. Say: "This supplier never reported our invoice, so its credit is at risk. The draft asks them to report it. Approved, and credit at risk falls to 2.23 lakh."
- Matched, not flagged. Do: click Workbench, click Matches, open a row marked One-to-many. Say: "Not everything odd is wrong. One payment settling two invoices is matched and left alone."

## If something goes wrong in the take

- The Run overlay stays up with an error: press Retry in it. If it fails twice, the API window from `start.cmd` shows why.
- A draft says "Written from a template": the cached draft did not match. Run `python -m app.drafts.precache --period 2025-09` from the backend folder (see CLAUDE.md), then record again.
- A number on screen differs from the line you are about to say: say what is on screen. The screen is the truth.

## Where each number comes from

| Line | Number | Screen |
|---|---|---|
| Credit at risk | Rs 2,81,615 (shown as Rs 2.82 L) | Dashboard, the four numbers |
| Credit found | Rs 3,098 | Dashboard, the four numbers |
| Net payable | Rs 34,96,926 (Rs 34.97 L) | Dashboard, the four numbers |
| Open Findings | 129 | Dashboard, Fix these first |
| Rate change invoice | INV-2526-01431, 28 percent on 25 Sep 2025, 18 percent since 22 Sep 2025, Rs 21,436 excess tax | Finding drawer |
| Excess tax after approving it | Rs 24,117 to Rs 2,681; Net payable to Rs 34,75,490 | Dashboard, the four numbers |
| Supplier not reporting | VEN041-0020, Titan Logistics Ltd, Rs 58,480 | Dashboard, Start here line |
| Credit at risk after approving it | Rs 2,23,135 (Rs 2.23 L) | Dashboard, the four numbers |
| Ring | Unity Infra Pvt Ltd (supplier) and Unity Motors Ltd (customer), one PAN; Rs 5,00,000 out on 30 Sep 2025, back on 2 Oct 2025; Rs 53,617 of credit this month, Rs 8.26 L over the year | Ring view |
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
