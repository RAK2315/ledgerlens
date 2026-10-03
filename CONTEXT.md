# LedgerLens

An AI copilot for Indian GST reconciliation. It matches a business's own records against each other and against what suppliers reported to the GST portal, prices every mismatch in rupees, explains it, and drafts the fix.

## Language

### Parties and records

**Company**:
The business whose books are being reconciled. In the demo, Sharma Traders Pvt Ltd, GSTIN 07AAACS1234F1ZU, Delhi.
_Avoid_: Client, taxpayer, user

**Party**:
Any business the Company trades with, identified by its GSTIN. A Party is a Supplier, a Customer, or both.
_Avoid_: Vendor (except in dataset column names), counterparty, entity

**Supplier**:
A Party the Company buys from.
_Avoid_: Vendor, seller

**Customer**:
A Party the Company sells to.
_Avoid_: Buyer, client

**Record**:
Any single row from a source: an Invoice, a Ledger entry, a Bank transaction or a GSTR-2B line.
_Avoid_: Transaction (ambiguous), entry (unless it is a Ledger entry), row

**Invoice**:
A tax invoice in the Company's books, either a purchase invoice (from a Supplier) or a sales invoice (to a Customer).
_Avoid_: Bill, receipt

**Credit note**:
A document that reduces an earlier Invoice's value and tax.
_Avoid_: Refund, return

**Ledger entry**:
One line in the Company's accounting books. A booking records an Invoice; a payment or receipt records money moving.
_Avoid_: Journal, voucher (the voucher is the parent document), posting

**Bank transaction**:
One debit or credit line on the Company's bank statement.
_Avoid_: Payment (a payment is one kind of Bank transaction), txn

**GSTR-2B line**:
One supply a Supplier reported against the Company's GSTIN, as shown in the Company's GSTR-2B statement for a Return period.
_Avoid_: 2B entry, portal record, supplier invoice

**Return period**:
The calendar month a GST return covers, written YYYY-MM.
_Avoid_: Tax period, filing month

### GST terms

**GSTIN**:
The 15-character GST registration number: 2-digit state code, the holder's 10-character PAN, an entity number, the letter Z and a check character.
_Avoid_: GST number, tax ID

**PAN link**:
Two or more Parties whose GSTINs carry the same PAN, meaning one owner behind several registrations.
_Avoid_: Related party (a legal term with a different meaning)

**HSN code**:
The goods or services classification code on an Invoice line that decides its GST rate. SAC is the services form; this project says HSN code for both.
_Avoid_: Product code, item code

**Effective rate**:
The GST rate for an HSN code on a given date. Rates change on fixed dates, such as the GST 2.0 change of 22 Sep 2025.
_Avoid_: Current rate, standard rate

**Tax type**:
Whether an Invoice is taxed as CGST plus SGST (supply within one state) or IGST (supply across states), decided by place of supply.
_Avoid_: Tax head, GST split

**ITC (input tax credit)**:
GST the Company paid on purchases that it may subtract from the GST it owes on sales.
_Avoid_: Input credit, tax refund

**Eligible ITC**:
ITC that meets every condition: the Supplier reported it, the tax is correct, it is not a blocked credit, and the Supplier was paid within 180 days.
_Avoid_: Valid ITC, claimable ITC

**ITC at risk**:
ITC the Company has claimed or will claim that is not Eligible ITC, in rupees. It is lost or reversed with interest unless fixed.
_Avoid_: Exposure, leakage

**ITC found**:
Eligible ITC that appears in GSTR-2B but is missing from the Company's books, in rupees. Money the Company is owed but has not claimed.
_Avoid_: Unclaimed ITC, recovered ITC

**Net payable**:
Output tax on sales minus Eligible ITC for a Return period, by tax type.
_Avoid_: Tax due, liability (alone)

### Reconciliation

**Run**:
One reconciliation of all Records for a Return period, producing Matches and Findings.
_Avoid_: Job, scan, analysis

**Match**:
A link between Records that represent the same economic event: Invoice to Ledger entry (booking), Invoice to Bank transaction (payment), or purchase Invoice to GSTR-2B line (supplier filing).
_Avoid_: Pair, link, reconciliation

**One-to-many match**:
A Match where one Bank transaction settles several Invoices, or several Bank transactions settle one Invoice.
_Avoid_: Bundled match, split match (these name the two directions only)

**Confidence**:
How sure the system is that a Match is right, from 0 to 1.
_Avoid_: Score, probability (in user-facing text)

**Band**:
Where a Match lands by Confidence: auto-matched, review, or unmatched.
_Avoid_: Bucket, tier, status

**Finding**:
One problem the system reports, tied to one or more Records, with a Finding type, a Rupee impact, a reason and a suggested action.
_Avoid_: Issue, flag, alert, error, discrepancy (all fine in casual speech, never in UI or code)

**Finding type**:
The kind of problem, from a fixed list such as missing in GSTR-2B, wrong tax rate or duplicate invoice.
_Avoid_: Error type, issue type (except when reading the dataset's labels sheet)

**Rupee impact**:
The money a Finding puts at stake, with its direction: ITC at risk, ITC found, excess tax, short tax, unaccounted payment or open payable.
_Avoid_: Amount, value, exposure

**Anomaly**:
A Finding raised because a Record looks unusual, not because it breaks a rule. Always carries the reason it looked unusual.
_Avoid_: Fraud (we never claim fraud), outlier (one kind of Anomaly)

**Supplier ring**:
A group of Parties connected by PAN links, shared bank accounts or shared addresses, where money may be moving in a circle.
_Avoid_: Fraud ring, shell network

**Draft**:
A proposed next step for a Finding, written for a human to approve: a Supplier email, a credit note request or a correcting Ledger entry.
_Avoid_: Action, suggestion, auto-fix

**Approval**:
A human accepting, editing or dismissing a Draft. Nothing leaves the system without one.
_Avoid_: Sign-off, confirmation

### Evaluation

**Planted error**:
A mistake deliberately written into the test data, recorded in the ground truth with its type and rupee effect.
_Avoid_: Injected bug, seeded issue

**Benign trap**:
A Record that looks like a mistake but is legitimate, such as an Invoice paid in two parts. A Finding on a Benign trap is a false alarm.
_Avoid_: Negative sample, decoy

**Ground truth**:
The full list of Planted errors and Benign traps, from the dataset's labels sheet plus the GSTR-2B augmentation.
_Avoid_: Answer key (that name belongs to the dataset's monthly liability sheet)

**Catch rate**:
The share of Planted errors of a Finding type that the system reports. Recall, in technical writing.
_Avoid_: Accuracy (too vague)

**False alarm rate**:
The share of reported Findings that are not Planted errors, or that sit on Benign traps.
_Avoid_: Error rate

## Scope cut line

**MVP** (the demo journey breaks without it): load the dataset and generate GSTR-2B lines; booking, payment and supplier-filing Matches with Confidence and Bands (supplier filing by rule score); one-to-many matches; tax checks (Effective rate including 22 Sep 2025, tax type, arithmetic, exempt and zero-rated); duplicates; Rule 37 and cancelled-GSTIN checks; rule-based Anomalies; ITC at risk, ITC found and Net payable per Return period; Findings with Rupee impact and reasons; the dashboard, Finding detail with evidence, Supplier ring view; Drafts from cached Claude output with template fallback; Catch rate and False alarm rate report.

**V2** (builds if MVP lands early): learned supplier-filing matcher; Isolation Forest Anomalies; Supplier scorecard ranking; ask in plain English; Excel and GSTR-3B draft export; uploading your own files.

**Stretch**: Benford screen; single-file executable; e-invoice IRN checks; GSTR-1 side reconciliation.

**Out**: login and accounts; more than one Company; live GST portal or bank connections; actually sending email; mobile app.
