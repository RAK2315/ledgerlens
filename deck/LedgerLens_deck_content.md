# LedgerLens deck content

Fintechstico V7.0, Problem statement 2: Intelligent tax reconciliation. Seven slides in the organiser's order. Images referenced below live in deck/images. Full-slide reference renders are in images/diagrams/slideN_full.png.

---

## Slide 1. Cover

Organiser cover page, unchanged.

---

## Slide 2. Problem statement

**Headline:** Businesses lose real money every month because their records don't match the government's

**Story strip** (four cards, left to right, arrows between them). Image: images/diagrams/problem_story.png

1. **A shop buys stock** (icon: receipt). Sharma Traders, a Delhi wholesaler, buys goods worth ₹1,00,000 and pays ₹18,000 GST on top to its supplier. Its accountant records the bill in the books.
2. **That GST can come back** (icon: indian-rupee). When the shop later sells goods, it can subtract the ₹18,000 it already paid from the GST it owes. This credit is called input tax credit (ITC), and it works like cash in hand.
3. **Only if every record agrees** (icon: file-warning). The supplier must report the same sale on the GST portal, the bill must charge the right rate, and the shop must pay within 180 days. Books, bank and portal must all tell one story.
4. **One mismatch, money gone** (icon: triangle-alert, red card). If even one detail differs, the credit is denied, the business pays interest, or a tax notice arrives months later. Often it surfaces only when it is too late to fix.

**Today, an accountant checks this by hand**
Every month, four sets of records are downloaded and compared line by line to find what does not match.
Flow: Accounting books, GST portal data, Bank statement, Bills and invoices, then Excel sheets (thousands of rows), then Slow and manual (and mistakes found late, or never).
- The same bill written two ways looks like a mismatch
- Problems are listed, but not what each one costs
- Bills entered twice and wrong tax rates slip through
- Fake suppliers are caught only after a tax notice

**Scale** (three stat tiles)
- **1.67 crore** businesses are registered under GST and face this every filing cycle. Source: GSTN, 30 Jun 2026
- **₹35,132 cr** of fake tax credit caught in just 7 months, much of it through fake supplier bills. Source: CBIC, Apr to Oct 2024
- **Oct 2025** new rules lock returns to what was already reported, so errors can't be fixed at the last minute. Source: GSTN advisories

**Footer:** Who feels it most: small and mid-sized businesses, and the CA firms that file GST for dozens of them every month.

**Speaker notes:** Tell it as a story. A shop buys stock and pays 18,000 rupees of GST. It can get that back as input tax credit, but only if every record agrees: the supplier reports the sale, the tax on the bill is right, and the bill is paid within 180 days. One mismatch and the money is gone. Today an accountant checks this by hand in Excel. Scale: 1.67 crore GST businesses, 35,132 crore of fake credit caught in seven months, and since Oct 2025 the rules are stricter.

---

## Slide 3. Team

**Team name** (placeholder) / Team members
Logo lockup: images/logo_ledgerlens.png. LedgerLens, Your AI assistant for GST checks.
Four member cards: Member name, College and year, Role (placeholders).
Footer: Problem statement 2: Intelligent tax reconciliation

---

## Slide 4. Solution

**Headline:** LedgerLens checks every bill, payment and tax record, shows the money at stake, and tells you what to do

**Four steps** (left column)
1. **Upload** (icon: database). Drop in the accounting books, bank statement and GST portal downloads. LedgerLens reads them as they are, so nobody retypes a single entry.
2. **Check** (icon: git-merge). Every bill is matched to its payment, its accounting entry and the supplier's GST filing, even when written differently. The tax rate on each bill is checked too.
3. **Explain** (icon: sparkles). Each problem shows the money involved: credit at risk if left unfixed, or credit owed but never claimed. A plain note says why, with both records as proof.
4. **Fix** (icon: mail-plus). It drafts the next step, like an email asking the supplier to correct their filing, or the entry that fixes the books. You review and approve in one click.

**Dashboard mockup** (right). Image: images/mockups/dashboard.png. Callouts above the two hero tiles: Money at risk (₹4.82 L ITC at risk), Money to claim (₹1.36 L ITC found). Mockup values are illustrative.

**Covers every requirement in the problem statement:** Matches bills and payments, Finds duplicates and mismatches, Checks the tax on every bill, Finds missing records, Flags suspicious patterns, Works out tax payable, Visual dashboard.

**Speaker notes:** LedgerLens does four things: upload, check, explain, fix. Point at the two coloured numbers: money you could lose, and money you can still claim. Every problem in the list has a rupee value and a next step. The green chips show we cover every requirement in the problem statement.

---

## Slide 5. Architecture

Image: images/diagrams/architecture_flow.png

**Step 1. Your records** (files a business already has): Accounting books (Tally, Excel or CSV), GST portal data (GSTR-2B and GSTR-1), Bank statement (CSV download), E-invoices (government invoice ID, IRN), Supplier status (active or cancelled GSTIN).

**Step 2. Clean up** (every file speaks one language): Reads any format (broken rows set aside, not lost), Money kept to the exact paisa (no rounding drift in totals), Checks every GSTIN is genuine (check digit and owner's PAN), Same bill, different spelling (INV/25-26/042 is bill 42), Right tax rate on any date (knows the 22 Sep 2025 change).

**Step 3. Match everything** (clear rules, not guesswork): Only same-supplier bills compared (GSTIN must match exactly), Three passes, each explained (exact, cleaned up, close match), No record used twice (best one-to-one pairing), One payment, many bills (and bills paid in parts), Sorted by certainty (matched, needs review, unmatched).

**Step 4. Find risk, explain** (how much, why, what next): Checks the tax on every bill (rate, type, maths, 180-day rule), Money at risk and tax payable (what you owe after credit), Spots unusual patterns (outlier and Benford's law tests), Rates suppliers, finds fake ones (shared owner, bank or address), AI writes the reason and the fix (Claude, checked by a person).

**Step 5. You review, act** (one screen, one click): Dashboard, Problem details with proof, Supplier network map, Ask in plain English, Export (Excel workpaper, GST draft).

**Runs on one laptop:** a local database (SQLite) keeps everything together, so the demo works even without internet.

**Maths by code, words by AI:** Every rupee figure comes from tested rules. The AI only explains and drafts. It can never change a number.

**Proven on test data:** We plant known mistakes in realistic books and count how many we catch, and how often we raise a false alarm.

**Speaker notes:** Five steps, left to right: your records, clean up, match everything, find risk and explain, you review and act. Two promises: maths by code and words by AI, so the AI never changes a number; and accuracy proven on test data with known mistakes. It runs on one laptop, even offline.

---

## Slide 6. Technology used

| Layer | Tools (what each does) |
|---|---|
| Website and dashboard | Next.js, TypeScript, Tailwind CSS, shadcn/ui (clean components), Recharts (charts), Cytoscape.js (supplier map) |
| Server and data | Python, FastAPI (connects screen and engine), Pydantic (checks every file), SQLite (local database), Polars (fast tables) |
| Matching engine | RapidFuzz (near-identical bill numbers), SciPy (best one-to-one pairing), scikit-learn (unusual pattern finder), NetworkX (links between suppliers) |
| AI assistant | Claude API (reasons and drafts), sees only the facts of one problem, saved answers (works offline), human approves every action |
| Reliability | Docker (runs anywhere), pytest (tests for every rule), Playwright (clicks through the demo), offline demo mode |

Logos: images/icons/*_brand.png

**Test data that knows the answers:** A full year (FY 2025-26) of books for a fictional trading company. Mistakes are planted on purpose and recorded, so we can count exactly what we catch and what we miss.
- 5,197 bills and invoices, 4,690 bank entries, 9,948 accounting entries
- 781 planted mistakes, 30 kinds of mistake, 1,368 honest traps
- Honest traps look like errors but are fine, such as bills paid in parts. A good system must leave them alone.
- Examples of planted mistakes: Bill entered twice, Old tax rate after 22 Sep, Wrong tax type, Tax maths error, Bill number typo, Missing entry, Payment with no bill, Money sent in a circle, Bills split to dodge limits, Invalid GSTIN, Credit over-claimed
- We add supplier filings (GSTR-2B) on top, so missing supplier reports and unclaimed credit can be tested too. Tax rates follow the official CBIC schedule.
- Scored on: Catch rate (share of real mistakes found) and False alarm rate (honest records wrongly flagged)

**Footer:** Why these tools: free, proven and widely used. Numbers are handled in Python, where every rule can be tested. Screens are built in TypeScript, where the experience is polished.

**Speaker notes:** Free, proven tools. The test data is a full year of books for a fictional company: about 5,200 bills, 4,700 bank entries and 9,900 accounting entries, with 781 planted mistakes and 1,368 honest traps that look like errors but are not. We score both how many mistakes we catch and how few false alarms we raise.

---

## Slide 7. Feature / USP

**Four pillars**
1. **Shows money, not rows** (icon: indian-rupee). Every problem shows the rupees at risk and the rupees you can still claim, sorted so the nearest deadline comes first. You fix what costs most, first.
2. **Every flag explains itself** (icon: scan-search). Each flag gives a plain-language reason, the GST rule behind it, both records side by side and how sure we are. Anyone can check it, so there is no black box.
3. **Fixes, not just finds** (icon: bot). It drafts the supplier email, credit note request or accounting correction for each problem. Nothing is sent until you approve, so you stay in control.
4. **Spots fake suppliers** (icon: network). It links suppliers that share an owner (PAN), bank account or address, revealing money moving in circles before the tax department finds it.

**Issue drawer mockup.** Image: images/mockups/issue_drawer.png
Tax rate mismatch, ₹42,000 at risk, 98% sure. UltraBuild Cements, UB/2526/1187, 24 Sep 2025.
Why this was flagged: Cement (HSN 2523) dropped from 28% to 18% on 22 Sep 2025. This invoice is dated 24 Sep but was billed at the old rate. The excess ₹42,000 should be corrected by a credit note before you claim it.
What to do: Ask UltraBuild for a ₹42,000 credit note. Until it arrives, claim credit only on the correct ₹75,600.
Drafted for you: credit note request, with Approve and send, Edit draft, Dismiss with note.

**Supplier graph mockup.** Image: images/mockups/supplier_graph.png
Money moving in a circle: You buy from Rudra Traders and sell to Nexa Agencies. Both share one PAN, and a third firm with a cancelled GSTIN shares their bank account. Credit at risk ₹2.23 L, 31 invoices in 60 days.

**Footer:** Also: it knows the GST rate change of 22 Sep 2025, links one payment to many bills, rates every supplier, and its accuracy is measured on test data, not guessed.

**Speaker notes:** Four reasons we are different. We show money, not rows. Every flag explains itself. We fix, not just find. We spot fake suppliers by linking firms that share an owner, bank account or address. The cement example is real: its GST rate dropped from 28 to 18 percent on 22 Sep 2025, and a bill two days later still charged 28.
