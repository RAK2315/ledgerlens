# 00 Overview

Vocabulary: CONTEXT.md. Conventions and stack: CLAUDE.md. ML recipe: ML_BUILD.md. This file fixes what the demo must show; 01 to 06 cover features, architecture, data model, design system, build plan and risks.

## Problem

Indian businesses must keep their books, bank statement and the GST portal in agreement to claim input tax credit. Today this is done by hand in spreadsheets; mismatches are found late, priced never, and fixed slowly. LedgerLens reconciles all of them for one Return period, prices every mismatch in rupees, explains it with evidence and drafts the fix.

## Scope rule

A feature belongs if it helps a judge see, within one demo month, money at risk or money found, why, and what to do about it. Anything else waits.

## Success metric

On the test split, Catch rate and False alarm rate per Finding type, reported from ML_REPORT.md and the engine evaluation, against the targets in ML_BUILD.md 5.5 and 7.3. Never quote demo-month numbers as accuracy.

## Users

- Finance lead or accountant at an MSME: reviews Findings, approves Drafts. Web app, laptop.
- CA firm staff: same screens, many Companies later (out of scope now, one Company only).

## The angle

Existing tools list mismatched rows. LedgerLens leads with rupees and deadlines, shows the evidence behind every flag, drafts the fix for approval, and links Suppliers by PAN to expose Supplier rings. Code decides every number; Claude only explains and drafts.

## Hard constraints

- Offline demo at NSUT: no live API calls on stage. Cached Claude output, template fallback.
- Every GST fact in UI or slides must be sourced (docs/RESEARCH.md to be created; deck/NOTES.md lists sources found so far).
- Data: data/source/tax_recon_dataset.xlsx plus generated GSTR-2B lines. No other data.
- Build window: from shortlisting until the onsite event, more than one week, pre-build allowed. Event date not yet known; ask the user.

## Demo journey (the one path that must work)

Demo month: September 2025, Sharma Traders Pvt Ltd, GSTIN 07AAACS1234F1ZU. September contains the GST 2.0 rate change (22 Sep 2025) and 45 non-benign planted errors.

1. Open the app. One button: Load demo company. A Run starts and the stages animate live: read records, clean up, match, check tax, find anomalies, work out money, write explanations (about 5 seconds, streamed from the backend).
2. Dashboard: ITC at risk, ITC found and Net payable as the three headline numbers; Match status (auto, review, unmatched, duplicate); ITC at risk by cause; top Findings ranked by Rupee impact and deadline.
3. Hero Finding: invoice INV-2526-01431, 25 Sep 2025, televisions (HSN 8528) sold to Delta Traders Private Limited at 28 percent when the Effective rate since 22 Sep 2025 is 18 percent. Excess tax Rs 21,436 (from the labels sheet; recompute in the engine). Finding detail shows the invoice against the rate table side by side, the rule, Confidence, plain reasons, what to do, and a Draft credit note to the Customer. Approve it: the Finding closes and the headline numbers update.
4. A Supplier-side Finding: a purchase invoice missing from GSTR-2B (Supplier did not file), priced as ITC at risk, with a Draft Supplier email.
5. A One-to-many match: one Bank transaction settling two Invoices, shown as matched, not flagged (a Benign trap left alone).
6. Supplier ring view: the PAN-linked Supplier and Customer from the augmentation, plus the cancelled-GSTIN Supplier, on the network graph with the explanation panel.
7. Liability: Net payable by tax type for the month, compared with what the GSTR-3B filing declared (tax_filings and answer_key sheets), showing the gap.
8. Proof: Catch rate and False alarm rate per Finding type on the test split.

Most impressive moment: step 3, approving the Draft and watching ITC numbers update, then step 6, the ring appearing on the graph.

## Notes carried over from the ideathon deck

- The deck's mockups are the design reference: deck/index.html (tokens in :root), renders in deck/images/mockups. Mockup numbers are illustrative; the app shows real ones.
- The deck's hero example (UltraBuild cement, HSN 2523) is not in the dataset. Do not fake it. Use INV-2526-01431 above. If the team wants a purchase-side GST 2.0 example, the dataset has VEN020-0041 (auto components, HSN 8708, 19 Jan 2026, 28 instead of 18 percent).
- The dashboard mockup shows GSTIN 07AAACS1234F1Z5, which fails the check digit. The app uses 07AAACS1234F1ZU. Fix the deck if it is re-submitted.
- Most GST 2.0 stale-rate cases in the dataset are on sales invoices (the Company overcharging Customers), not purchases. Findings on sales invoices have Rupee impact type excess tax, not ITC at risk.

## Inputs

- plan/inputs/earlier-spec.md: the parts of the user's earlier Claude-web spec that still apply (API list, screens, demo mode, research questions).
