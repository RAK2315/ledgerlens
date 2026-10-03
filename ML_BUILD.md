# LedgerLens ML build guide

This guide tells you how to build, test and run the machine learning part of LedgerLens. You need only two things: this file and the dataset file tax_recon_dataset.xlsx. Everything else is explained here.

If you follow it from top to bottom you end with trained model files, a results report and a command-line tool.

## 0. The project in one minute

LedgerLens helps an Indian business check its GST records for one month. It compares four sets of records and reports every mismatch in rupees:

- the invoices the business raised or received,
- the entries in its accounting books,
- the lines on its bank statement,
- what its suppliers reported to the GST portal.

One rule runs through the whole project: code decides, AI explains. Every rupee number comes from plain, tested code. Machine learning is used only where simple rules break easily, which is deciding whether two records are the same thing when they are written a little differently.

### Words used in this guide

| Word | Meaning |
|---|---|
| Company | The business whose books we check. In our data: Sharma Traders Pvt Ltd, Delhi. |
| Party | Any business the Company trades with. |
| Supplier | A Party the Company buys from. The dataset calls it VENDOR. |
| Customer | A Party the Company sells to. |
| Invoice | A tax invoice in the Company's books. A purchase invoice comes from a Supplier. A sales invoice goes to a Customer. |
| Credit note | A document that lowers the value and tax of an earlier invoice. |
| Ledger entry | One line in the Company's accounting books. A booking entry records an invoice. A payment or receipt entry records money moving. |
| Bank transaction | One debit or credit line on the bank statement. |
| GSTIN | The 15-character GST registration number: 2-digit state code, the owner's 10-character PAN, one entity character, the letter Z, and one check character. |
| PAN | The 10-character tax ID of the owner. Two GSTINs with the same PAN have the same owner. |
| HSN code | The code on an invoice that says what was sold. It decides the GST rate. |
| CGST, SGST, IGST | The three kinds of GST. A sale inside one state has CGST plus SGST. A sale across states has IGST. |
| ITC (input tax credit) | GST the Company paid on purchases. It can subtract this from the GST it owes on sales. |
| GSTR-2B line | One purchase that a Supplier reported against the Company's GSTIN, as shown in the Company's monthly GSTR-2B statement. |
| Return period | The calendar month a GST return covers. |
| Match | A link between two records that describe the same event, for example an invoice and its bank payment. |
| Confidence | How sure we are that a Match is right, from 0 to 1. |
| Band | Where a Match lands by Confidence: auto (accepted), review (a person checks it), unmatched. |
| Finding | One problem the system reports, with its rupee effect and a reason. |
| Planted error | A mistake put into the dataset on purpose, listed in the labels sheet. |
| Benign trap | A record that looks wrong but is fine, for example an invoice paid in two parts. Reporting it is a false alarm. |
| Paise | 1 rupee is 100 paise. All money in code is whole paise, never decimals. |

### What is ML here and what is not

| Part | Kind | Job | Build |
|---|---|---|---|
| A. Booking matcher | Trained classifier | Is this invoice and this ledger entry the same transaction? | First |
| B. Payment matcher | Trained classifier | Does this bank transaction pay this invoice? | First |
| C. Anomaly detector | Rules plus Isolation Forest | Flag unusual invoices and bank flows, with a reason | Second |
| D. Supplier filing matcher | Trained classifier | Is this purchase invoice and this GSTR-2B line the same purchase? | Later |
| E. Benford screen | Statistics | First-digit check over the whole Company | Optional |

Not ML, and not covered here: tax rate checks, duplicate checks, the search for one payment covering several invoices, and the tax owed for the month. Those are plain rules in the rest of the app. The models here only return scores and reasons.

## 1. What you need

### 1.1 Computer

- Windows 11, macOS or Linux. 8 GB RAM is enough. No GPU.
- Python 3.10.11. Python 3.11 or 3.12 also work.
- A full training run takes under 5 minutes.

### 1.2 Packages

Create the file ml/requirements.txt with exactly these lines:

```
numpy==2.2.6
pandas==2.3.3
scipy==1.15.3
scikit-learn==1.7.2
joblib==1.6.0
rapidfuzz==3.14.5
networkx==3.4.2
openpyxl==3.1.5
pydantic==2.13.5
pytest==9.1.1
```

Notes:

- Keep networkx at 3.4.2 on Python 3.10. Newer versions need Python 3.11.
- We use scikit-learn's HistGradientBoostingClassifier, not LightGBM or XGBoost. It is just as good for a table this small, needs no extra install, and accepts missing values.
- rapidfuzz gives fast text similarity scores.
- No deep learning. The data is a few thousand rows. A neural network would be slower, harder to explain and no better.

### 1.3 Setup

Put the dataset at data/source/tax_recon_dataset.xlsx. Then, from the project folder:

Windows PowerShell:

```
python -m venv ml\.venv
ml\.venv\Scripts\python -m pip install --upgrade pip
ml\.venv\Scripts\python -m pip install -r ml\requirements.txt
ml\.venv\Scripts\python -m pip install -e ml
```

macOS or Linux:

```
python -m venv ml/.venv
ml/.venv/bin/python -m pip install --upgrade pip
ml/.venv/bin/python -m pip install -r ml/requirements.txt
ml/.venv/bin/python -m pip install -e ml
```

The file ml/pyproject.toml names the package ledgerlens_ml and asks for Python 3.10 or newer, below 3.13.

## 2. Folder layout

```
data/
  source/tax_recon_dataset.xlsx   the dataset
  derived/                        files made by the augment command (section 3.5)
ml/
  pyproject.toml
  requirements.txt
  ledgerlens_ml/
    __init__.py     the functions other code may import (section 9.1)
    config.py       all fixed numbers: seed, date windows, thresholds, split months, paths
    data.py         reads the workbook, checks it, returns clean tables
    augment.py      makes the GSTR-2B lines and extra labels
    normalise.py    cleans invoice numbers and party names
    parties.py      works out which Party a bank line belongs to
    candidates.py   picks which pairs of records are worth scoring
    features.py     turns each pair into numbers
    matcher.py      trains, saves, loads and runs a matcher
    anomaly.py      anomaly rules and Isolation Forest
    evaluate.py     writes the results report
    cli.py          the commands
    __main__.py     lets you run python -m ledgerlens_ml
  tests/            one test file per module, plus fixtures/mini.xlsx
  artifacts/        trained model files and their result cards
  reports/          the results report
```

Four rules keep the code easy to change:

- Only data.py reads the workbook. Every other module is given tables. If a column is renamed, one file breaks, not ten.
- features.py never touches files or models. Tables in, table out. So every feature can be tested, and training and live scoring always compute the same thing.
- Only matcher.py and anomaly.py use scikit-learn. To change the model type you change only those files.
- Other code imports only from ledgerlens_ml/__init__.py.

## 3. The dataset

### 3.1 The file

- Path: data/source/tax_recon_dataset.xlsx
- SHA-256: c49199eb35be2743ed9cdd9cf2db23996472c5194a01219fc49d01d0e084ab23
- data.py checks this hash every time it loads the file and stops with an error if it differs. That way every result names the exact data it came from.
- It holds one financial year (1 April 2025 to 31 March 2026) of records for a made-up trading company in Delhi (state code 07). Mistakes were put in on purpose, and the file lists every one of them.
- The workbook does not name the company. config.py sets the name Sharma Traders Pvt Ltd and the GSTIN 07AAACS1234F1ZU.

### 3.2 Sheets and columns

data.py loads each sheet with exactly these columns. A missing or unknown column is an error.

| Sheet | Rows | Columns | Used for |
|---|---|---|---|
| invoices | 5,197 | invoice_id, doc_type (INVOICE, CREDIT_NOTE), invoice_type (SALES, PURCHASE), invoice_date, due_date, party_id, party_name, party_gstin, party_state_code, place_of_supply, hsn_sac, category, taxable_value, tax_rate_pct, cgst, sgst, igst, total_tax, invoice_total, currency, original_invoice_id (can be empty) | Left side of every matcher |
| bank_transactions | 4,690 | txn_id, txn_date, value_date, bank_account, direction (DEBIT, CREDIT), amount, currency, counterparty_name, counterparty_account, payment_mode, utr, narration, closing_balance | Right side of the payment matcher |
| accounting_ledger | 9,948 | entry_id, voucher_no, posting_date, fiscal_period, voucher_type (SALES, PURCHASE, PAYMENT, RECEIPT, CREDIT_NOTE, JOURNAL, TAX_PAYMENT), ledger_account, party_id, party_name, invoice_ref (can be empty), taxable_amount, cgst, sgst, igst, total_tax, total_amount, debit, credit, utr_ref, narration, entered_by, entry_timestamp | Right side of the booking matcher |
| tax_rates | 15 | category_code, category, hsn_sac, supply_type, gst_rate_pct, cgst_pct, sgst_pct, igst_pct, effective_from, effective_to (can be empty), is_exempt | The correct rate for a date |
| party_master | 120 | party_id, party_name, party_type (CUSTOMER 70, VENDOR 50), gstin, pan, state_code, state, payment_terms_days | Finding the Party |
| tax_filings | 12 | period, return_type, due_date, filing_date, outward_taxable_value, output_cgst, output_sgst, output_igst, total_output_tax, itc_cgst, itc_sgst, itc_igst, total_itc_claimed, net_tax_payable, status | Not used by ML |
| answer_key | 12 | period, true_outward_taxable_value, true_output_tax, true_eligible_itc, itc_blocked_invalid_supplier_gstin, true_net_tax_liability, declared_total_output_tax, declared_total_itc, declared_net_tax_payable, liability_gap_inr | Not used by ML |
| labels | 2,149 | issue_id, issue_type, issue_category, severity, entity_type, entity_id, related_entity_id, field_affected, expected_value, recorded_value, financial_impact_inr, description, is_benign | The list of planted errors and benign traps |
| links | 5,519 | invoice_id, booking_entry_id (43 empty), txn_id (819 empty), receipt_entry_id, allocated_amount, link_type (FULL 3,898, UNPAID_OPEN 722, PARTIAL 629, BUNDLED 180, CREDIT_NOTE 60, DUPLICATE_INVOICE_UNPAID 17, DUPLICATE_PAYMENT_EXCESS 13) | The true matches, used to train A and B |

What data.py does to every sheet:

- Money becomes whole paise (rupees times 100, rounded half up). The column name gets _paise at the end: taxable_value becomes taxable_value_paise, amount becomes amount_paise, financial_impact_inr becomes financial_impact_paise.
- Dates become real date values.
- IDs are kept exactly as written.

### 3.3 Facts measured on this file

The profile command prints these. They shaped the design. If your numbers differ, something in data.py is off.

- Purchase invoices per month: 144 to 217. Each Supplier has about 43 in the year.
- All 120 party GSTINs pass the check-character test.
- Purchase invoice numbers look like VEN001-0001. Sales invoice numbers look like INV-2526-00001. Credit notes look like CN-2526-0038. All 60 credit notes are sales credit notes.
- Bank narrations look like NEFT/UTR/NAME/REFERENCE. 67.8 percent quote the invoice number as written. 24.9 percent quote it in another form (ven0420001, inv252601229, or only the serial such as 0035). 7.3 percent have no reference.
- 76.6 percent of bank names equal a name in party_master. The rest are cut at 22 characters, written without spaces (BHARATSYSTEMSPVTLTD) or shortened (PRIME MEDIA).
- 22 parties share a cleaned name with another party (Evergreen Infra & Co and Evergreen Infra Private Limited). So a name alone cannot always pick the Party.
- Every Party uses exactly one counterparty_account, and no account is shared.
- 99.5 percent of ledger invoice_ref values exist in invoices. The rest are planted typos: wrong year (INV-2425-02759 for INV-2526-02759), letter O for zero (INV-2526-O2328), swapped digits, dropped digits (INV-252-02921).
- Days from invoice to payment: lowest minus 30 (planted, paid before the invoice), median 25, highest 101.
- For fully paid invoices, payment divided by invoice total runs from 0.903 to 1.048, median 1.0.
- An invoice has at most 2 bank transactions (paid in parts). A bank transaction covers at most 2 invoices (bundled).

### 3.4 What counts as the truth

- Booking matcher: a pair (invoice, ledger entry) is a true match if the links sheet has that invoice_id with that booking_entry_id.
- Payment matcher: a pair (invoice, bank transaction) is a true match if the links sheet has that invoice_id with that txn_id.
- Every other pair we score is a non-match.
- Anomaly detector: it is not trained on labels. Labels with issue_category ANOMALY are used only to pick thresholds and to report results.
- Benign traps (is_benign is true: BUNDLED_PAYMENT, CREDIT_NOTE, LEGIT_OPEN_INVOICE, NON_INVOICE_TXN, PARTIAL_PAYMENT, ROUNDING_NOISE) must not be reported. Any report on one is a false alarm.
- One known clash, stated openly: a purchase invoice left unpaid for more than 180 days is marked LEGIT_OPEN_INVOICE (benign) in the workbook. But under Rule 37 the credit on a purchase is at risk when the Supplier is not paid within 180 days. So we treat it as a real problem, score it against our own labels from section 3.5, and leave those invoices out of the false alarm count. The report must say this.

### 3.5 Augmentation: making the GSTR-2B lines

The workbook has no data on what Suppliers reported to the GST portal. The product needs it, so augment.py makes it. The result is the same every time (seed 42).

Command:

```
python -m ledgerlens_ml augment
```

It writes three files in data/derived:

- gstr2b.csv: the GSTR-2B lines
- augment_labels.csv: the extra planted errors
- augment_manifest.json: seed, rates, the workbook hash, counts, and the choices listed below

Steps, in order:

1. Pick the ring Supplier: the Supplier behind the earliest CIRCULAR_FLOW label (money sent out and returned). Pick one Customer at random with the seed.
2. Give each of the 50 Suppliers a filing behaviour by a seeded shuffle: 35 reliable, 10 late, 5 non_filer. The ring Supplier is always reliable.
3. For each purchase invoice:
   - reliable Supplier: one line in the invoice month.
   - late Supplier: one line in the next month. Label PERIOD_SHIFT.
   - non_filer Supplier: no line. Label MISSING_IN_2B, impact = the invoice's total tax.
   - an invoice the workbook labels DUPLICATE_INVOICE gets no line and no label, because the Supplier issued it only once.
4. Change some lines the way real Suppliers do. Each change is drawn separately:
   - 30 percent: the invoice number is written in the Supplier's own style. VEN001-0001 becomes 1, or VEN/001/0001, or INV-0001. This is not an error. The matcher must still match it.
   - 3 percent: the taxable value differs by 2 to 15 percent, and the tax with it. Label GSTR2B_VALUE_MISMATCH, impact = the tax difference.
   - 2 percent: the date moves 1 to 10 days later. If that crosses into the next month, label PERIOD_SHIFT.
5. Add extra lines equal to 2 percent of purchase invoices (42 lines). Each copies the shape of a real invoice from a filing Supplier, with a new invoice number that is not in the books. Label MISSING_IN_BOOKS, impact = the tax. This is credit the Company could claim but has not.
6. Rule 37: every purchase invoice that links marks UNPAID_OPEN and that is dated more than 180 days before 31 March 2026 gets the label RULE_37_UNPAID_180, impact = total tax.
7. Cancelled Suppliers: the two non_filers with the most invoices are marked as having a cancelled GSTIN from the date of their middle invoice. Invoices on or after that date get the label CANCELLED_GSTIN.
8. The ring: the chosen Customer's PAN, and characters 3 to 12 of its GSTIN, are replaced by the ring Supplier's PAN. The check character is recomputed. Both parties get the label PAN_LINKED_RING.

gstr2b.csv columns: line_id (2B-000001 onwards), gstin_supplier, trade_name, invoice_number, invoice_type (always R), invoice_date, invoice_value, place_of_supply, reverse_charge (always N), rate, taxable_value, igst, cgst, sgst, cess, return_period (MMYYYY), itc_availability (Y), reason, source_invoice_id.

- Money in the CSV is in rupees with two decimals. data.py turns it into paise when loading.
- source_invoice_id is the answer (which invoice the line came from). It is only for measuring results. Never use it as a feature.

augment_labels.csv has the same columns as the labels sheet plus source = augment. Two new entity_type values appear: GSTR2B_LINE (entity_id is the line_id) and PARTY (entity_id is the party_id).

What you get with seed 42:

- 1,931 lines, 42 of them not in the books.
- Labels: MISSING_IN_2B 220, PERIOD_SHIFT 415, GSTR2B_VALUE_MISMATCH 51, MISSING_IN_BOOKS 42, RULE_37_UNPAID_180 35, CANCELLED_GSTIN 51, PAN_LINKED_RING 2.
- Ring: Supplier VEN-009 Unity Infra Pvt Ltd and Customer CUS-007 Unity Motors Ltd. The round trip is Rs 5,00,000 out on 30 Sep 2025 and back on 2 Oct 2025.
- Cancelled: VEN-006 from 2 Sep 2025, VEN-010 from 29 Oct 2025.

When the derived files exist, load_dataset uses them. The parties table gains three columns (filing_behaviour, gstin_status, cancelled_from), the ring Customer gets its new PAN and GSTIN in the parties table and on its invoices, and the extra labels are added to the labels table.

If the lines look too clean, raise the rates in config.py and run augment again. Never edit the CSV by hand.

### 3.6 Train, validation and test months

We split by invoice date, because the real product always scores a month it has not seen.

| Split | Months | Used for |
|---|---|---|
| train | April to December 2025 | fitting the models |
| validation | January 2026 | picking thresholds, when to stop training, calibration |
| test | February and March 2026 | the final numbers in the report |

Rules:

- A pair belongs to the split of its invoice.
- Averages such as a Party's usual invoice size are computed from train months only and saved with the model.
- Never tune anything on test.
- Quote only test numbers as accuracy.

## 4. Cleaning (normalise.py, parties.py)

### 4.1 Invoice numbers

normalise_invoice_id(raw) turns different spellings of one invoice number into the same text. It is used on invoice IDs, ledger invoice_ref values, references in bank narrations and GSTR-2B invoice numbers.

Steps:

1. Uppercase and trim.
2. Fix look-alike letters inside numbers: O becomes 0, I and L become 1, S becomes 5. Only when the letter is followed by a digit and is not preceded by a letter.
3. Remove a leading INV, INVOICE, TAX INVOICE, BILL or NO, when followed by a separator or a digit.
4. Split on separators: space, slash, hyphen, underscore, dot.
5. A code written without separators is split too: VEN0420001 becomes VEN042 and 0001, and 252601229 becomes 2526 and 01229.
6. Remove one financial-year part (2526, 2425, FY26, FY2526) if at least 3 digits remain.
7. Remove leading zeros from the last number only, then join the parts.

id_serial(raw) returns only that last number without leading zeros.

These cases must pass (write them as tests first):

| Input | normalise_invoice_id | id_serial |
|---|---|---|
| INV-2526-02759 | 2759 | 2759 |
| INV-2425-02759 | 2759 | 2759 |
| INV-2526-O2328 | 2328 | 2328 |
| INV-252-02921 | 2522921 | 2921 |
| VEN042-0001 | VEN0421 | 1 |
| ven0420001 | VEN0421 | 1 |
| INV VEN002-0001 | VEN0021 | 1 |
| VEN/001/0001 | VEN0011 | 1 |
| inv252601229 | 1229 | 1229 |
| CN-2526-0038 | CN38 | 38 |

About INV-252-02921: 252 is not a year, so it stays and the cleaned forms differ. That is fine. The serial still matches, and the raw text is only one edit away from the right one. The similarity features in section 5.2 catch it.

narration_id_tokens(narration) returns the invoice references in a bank narration: the part after the third slash, split on commas, keeping only pieces that look like a reference. So NEFT/U/ACME/INV-2526-00001,INV-2526-00002 gives two references, and NEFT/U/HDFC BANK/BANK CHARGES gives none.

### 4.2 Party names and finding the Party for a bank line

normalise_party_name(raw): uppercase, turn & into AND, drop punctuation, drop the legal words at the end (PVT, PRIVATE, LTD, LIMITED, LLP, CO, AND). A name with no spaces loses a glued-on ending such as PVTLTD.

resolve_bank(bank, parties, invoices) adds three columns to the bank table: resolved_party_id, resolve_score (0 to 100) and resolve_method. For each bank line it tries, in order:

1. invoice_ref: a reference in the narration, once cleaned, equals a cleaned invoice ID. Use that invoice's Party, score 100. A DEBIT is checked only against purchase invoices and a CREDIT only against sales invoices. Otherwise a bare Supplier serial such as 0035 would be read as sales invoice 35.
2. account: the bank account on this line was seen on lines solved by step 1. Use the Party those lines point to, score 100. This step exists because of the same-named parties in section 3.3. Without it the name step is wrong on about 12 percent of the lines it handles.
3. name: the closest cleaned name, using the higher of rapidfuzz token_set_ratio and the plain ratio with spaces removed. Accept only at 88 or above. On a tie prefer a Supplier for a DEBIT and a Customer for a CREDIT, then the closer legal ending.
4. Otherwise no Party (bank charges, salaries, tax payments).

One more rule: if the name scores 95 or more and points to a different Party than the reference does, trust the name, unless the account agrees with the reference. A mistyped reference is more likely than a wrong name.

What to expect: 100.0 percent of bank lines that have a true match get the right Party. Without the account step it is 98.6 percent.

### 4.3 Text similarity

From rapidfuzz: fuzz.ratio, fuzz.token_set_ratio and DamerauLevenshtein.normalized_similarity. Features store them as numbers from 0 to 1.

## 5. Matchers A and B

### 5.1 Picking pairs to score (candidates.py)

We cannot score every invoice against every record. So for each invoice we keep only pairs that could be right.

Booking matcher, for each invoice:

- ledger entries with voucher_type PURCHASE for a purchase invoice, SALES for a sales invoice, CREDIT_NOTE for a credit note,
- the same party_id,
- posting date from 45 days before to 75 days after the invoice date,
- at most 20, keeping those closest in amount.

Payment matcher, for each invoice (credit notes are skipped):

- bank DEBIT for a purchase invoice, CREDIT for a sales invoice,
- the bank line's resolved Party equals the invoice's Party, or the narration quotes the invoice,
- transaction date from 45 days before to 120 days after the invoice date,
- at most 20 closest in amount, but a line that quotes the invoice is always kept.

Hard check before training: at least 99.5 percent of the true pairs in train must be among the picked pairs. If not, widen the windows first. What to expect: 100.0 percent for booking (3,852 true pairs) and 100.0 percent for payment (3,976).

### 5.2 Features (features.py)

One row per pair. All numbers. Empty values are allowed.

| Feature | Meaning | Booking | Payment |
|---|---|---|---|
| id_exact | the two IDs are identical | yes | the narration contains the invoice ID |
| id_norm_exact | cleaned IDs are equal | yes | for any reference in the narration |
| id_serial_equal | serials are equal | yes | yes |
| id_ratio | fuzz.ratio on cleaned IDs, 0 to 1 | yes | best over the references |
| id_dl_sim | Damerau-Levenshtein similarity on raw uppercase IDs | yes | best over the references |
| id_missing | the other side has no ID | yes | yes |
| amt_rel_diff | difference in totals divided by the larger total | yes | yes |
| amt_within_1 | totals differ by at most Rs 1 | yes | yes |
| amt_ratio | other side's amount divided by the invoice total | yes | yes |
| amt_log_left | log10 of the invoice total in rupees | yes | yes |
| tax_rel_diff | like amt_rel_diff, on total tax | yes | no |
| taxable_rel_diff | like amt_rel_diff, on taxable value | yes | no |
| date_diff_days | other side's date minus invoice date | yes | yes |
| date_abs_diff | the same without the sign | yes | yes |
| same_period | same calendar month | yes | no |
| party_score | 1.0 for booking; resolve_score divided by 100 for payment, 0 if the Party differs | yes | yes |
| party_method_ref | the Party was found from the invoice reference | no | yes |
| amt_rank | 1 = closest in amount among this invoice's pairs | yes | yes |
| date_rank | 1 = closest in date among this invoice's pairs | yes | yes |
| n_candidates | how many pairs this invoice has | yes | yes |

Notes:

- Amounts are compared by size, so a credit note (negative in invoices, positive in the ledger) compares correctly.
- When the other side has no ID, id_ratio and id_dl_sim are empty and the other ID features are 0.
- The feature order is fixed in config.py (MATCHER_FEATURES_A and MATCHER_FEATURES_B) and saved with the model. Scoring refuses to run if the saved list differs from the code's list.

### 5.3 Model and training (matcher.py)

```
HistGradientBoostingClassifier(
    learning_rate=0.08,
    max_leaf_nodes=31,
    min_samples_leaf=20,
    l2_regularization=1.0,
    early_stopping=False,
    class_weight="balanced",
    random_state=42,
)
```

Steps:

1. Build pairs and features. Mark each pair as a true match or not (section 3.4). Give it the split of its invoice.
2. Weights: a true pair gets weight 3.0 if its invoice or its other record has one of these hard-case labels: INVOICE_ID_MISMATCH, AMOUNT_MISMATCH, DATE_MISMATCH, PAYMENT_AMOUNT_MISMATCH, PAYMENT_BEFORE_INVOICE, PARTIAL_PAYMENT, BUNDLED_PAYMENT. Everything else gets 1.0. These cases are rare and they are what matters most.
3. Train with 20 trees, then 40, 60 and so on up to 400 (warm_start=True keeps the earlier trees). After each step measure average precision on the validation month. Stop after 3 steps with no gain. Then train a fresh model with the best tree count.
4. Calibrate on the validation month, so the score can be read as a probability: CalibratedClassifierCV(FrozenEstimator(model), method="isotonic").fit(X_val, y_val). FrozenEstimator is in sklearn.frozen. The older cv="prefit" option is deprecated in scikit-learn 1.7. The calibrated score is the Confidence.
5. Baseline, a simple rule score to compare against: 0.45 x id_dl_sim + 0.30 x (1 minus min(amt_rel_diff x 10, 1)) + 0.15 x (1 minus min(date_abs_diff / 60, 1)) + 0.10 x party_score. An empty id_dl_sim counts as 0.
6. Ship the model only if its F1 on test beats the baseline by at least 0.01. Otherwise ship the baseline through the same functions and say so in the card. Either way the rest of the app works.

### 5.4 From scores to matches

1. Assignment. Each invoice gets at most one partner and each record is used at most once. Build groups of invoices and records connected by pairs scoring at least 0.30. In each group run scipy.optimize.linear_sum_assignment on cost = 1 minus Confidence. Pairs under 0.30 are never used.
2. Bands. Confidence 0.90 or more is auto. 0.70 to 0.90 is review. Below 0.70 is unmatched. The auto threshold is the lowest of 0.90, 0.95 and 0.98 that gives at most 1 percent wrong auto matches on the validation month.
3. Leftovers. An invoice paid in two parts, or a payment covering two invoices, cannot be fully solved one to one. The second half is left unmatched on purpose. A separate rule-based search in the app (same Party, 60-day window, exact sum on paise) picks those up. The matcher does not try to learn it.
4. Reasons. Every match carries up to three plain sentences built from its feature values: one about the invoice number, one about the amount, one about the date. Examples: "Invoice number matches after removing prefix and year", "Amount differs by Rs 1.40", "Paid 3 days after the invoice date".
5. Scoring one month. score_pairs(kind, ds, period) also scores invoices from 120 days before to 60 days after the month, so neighbours compete for the same records. It returns only that month's invoices.

### 5.5 What we measure, and the targets

On the test split:

- Pair level: precision, recall and F1 at the auto threshold, and average precision.
- Invoice level: the share of invoices whose assigned partner (review band or better) is one of its true partners. Invoices with no true partner are reported separately as the share left unmatched.
- Hard cases: for each hard-case label, the share of its true pairs reaching auto, and reaching review.
- Benign traps: the share of PARTIAL_PAYMENT, BUNDLED_PAYMENT and ROUNDING_NOISE true pairs that reach review or better.

| Measure | Booking target | Payment target |
|---|---|---|
| Pair F1 at the auto threshold | 0.97 | 0.95 |
| Invoice-level accuracy | 0.98 | 0.95 |
| INVOICE_ID_MISMATCH pairs reaching review | 0.90 | 0.85 |
| Benign traps matched | 0.95 | 0.95 |
| Wrong auto matches | at most 1 percent | at most 1 percent |

These are targets, not claims. Report the real numbers whatever they are. If a target is missed, the report says so in its first lines.

What a correct build gets on the test split. Use it to check your own run; small differences are normal:

| Measure | Booking | Payment |
|---|---|---|
| Shipped | model | model |
| Pair F1, model | 0.9989 | 1.0000 |
| Pair F1, baseline | 0.9819 | 0.7495 |
| Invoice-level accuracy | 0.9989 | 0.9964 |
| Wrong auto matches | 0.23 percent | 0 percent |
| Hard cases and benign traps reaching review | all | all |

Limits to state with these numbers: the payment test split has only 288 true pairs and no INVOICE_ID_MISMATCH pair, so that target is not measured there. The data is synthetic, so real books will be harder.

### 5.6 Files written by training

- ml/artifacts/matcher_booking.joblib and matcher_payment.joblib: a dict with kind, model (the calibrated model, or the word baseline), features, thresholds (auto, review), frozen_aggregates, model_version, trained_at, data_sha256.
- ml/artifacts/matcher_booking.card.json and matcher_payment.card.json: the same details plus every measure from 5.5, the feature importances and the baseline comparison.

## 6. Matcher D: supplier filing (later)

The same recipe as section 5, with these changes:

- Left side: purchase invoices. Right side: the lines in data/derived/gstr2b.csv.
- Pairs to score: the Supplier GSTIN must be exactly equal (never fuzzy-match a GSTIN), the line's Return period is the invoice month or the next month, at most 10 per invoice.
- Extra features: period_offset (0 or 1), rate_equal, and whether both sides are IGST or both are CGST plus SGST.
- Truth: source_invoice_id in gstr2b.csv. Drop that column before building features.
- Targets: pair F1 0.97, and 0.95 recall on lines whose invoice number is written in the Supplier's own style.
- Output: ml/artifacts/matcher_gstr2b.joblib and its card.

Until this exists, the app matches purchase invoices to GSTR-2B lines with a rule score.

## 7. Anomaly detector C

Every flag must come with a reason a finance person accepts. So we use clear rules for the known patterns, and an Isolation Forest for what the rules miss.

### 7.1 Rules (anomaly.py)

| Rule | Fires when | Label it should catch |
|---|---|---|
| outlier_amount | taxable value is at least 10 times the Party's train median (or the category median when the Party has fewer than 5 train invoices) | OUTLIER_AMOUNT |
| round_amount_spike | taxable value is at least Rs 1,00,000 and divisible by Rs 10,000 | ROUND_AMOUNT_SPIKE |
| threshold_splitting | 3 or more invoices from one Supplier within 4 days, each between 90 and 100 percent of the Rs 2,00,000 approval limit | THRESHOLD_SPLITTING |
| vendor_burst | 6 or more invoices from one Supplier within 3 days, each below that Supplier's train median | VENDOR_BURST |
| weekend_large | dated on a Sunday and taxable value above the 95th percentile of train | WEEKEND_LARGE_TXN |
| circular_flow | a bank DEBIT to a Party, divisible by Rs 50,000, with no invoice, followed within 10 days by a CREDIT of the same amount from the same Party | CIRCULAR_FLOW |

All numbers live in config.py. They are starting points. Tune them on validation, then fix them. features.train_aggregates already gives the train medians and the 95th percentile.

### 7.2 Isolation Forest

Fit on train-month invoices:

```
IsolationForest(n_estimators=300, max_samples="auto", contamination="auto", random_state=42)
```

Features: log10 of taxable value, ratio to the Party's train median, ratio to the category's train median, z-score inside the category, divisible by Rs 10,000, day of week, is Sunday, day of month, invoices from the same Party in the last 3 days, and in the last 7 days, days since the Party's first invoice, tax rate, across states or not.

- Score: score_samples with the sign flipped, so higher means more unusual.
- Threshold: on validation, the score at which at least half the flags are labelled anomalies. Then fix it.
- Reason: the two features furthest from normal, in plain words, for example "15 times this supplier's usual invoice" or "Dated on a Sunday".

### 7.3 Targets

On test, per anomaly label: recall, precision and number of flags. Targets: each rule catches 0.90 of its own label, overall precision 0.50, false alarms on benign traps at most 2 percent. Report the real numbers.

### 7.4 Files

ml/artifacts/anomaly_invoice.joblib (forest, feature list, saved medians, threshold, rule numbers) and anomaly_invoice.card.json.

## 8. Benford screen E (optional)

Take the first digit of the taxable value of every purchase invoice in the period and compare the spread with Benford's law, using mean absolute deviation. Do this for the whole Company only. About 43 invoices per Supplier is too few to do it per Supplier. Show the chart labelled "screening only". Do not show a pass or fail verdict unless the cut-off values are checked against a published source and that source is written in ml/reports.

## 9. Functions and commands

### 9.1 Functions other code may use (ledgerlens_ml/__init__.py)

```python
MODEL_VERSION: str                      # "2026.10.0"

load_dataset(path=None, derived_dir=None, expected_sha256=...) -> Dataset
# Dataset holds tables: invoices, bank, ledger, tax_rates, parties, filings,
# answer_key, labels, links, gstr2b (None until augment has run),
# plus manifest (the augment manifest) and sha256.
# Pass expected_sha256=None only for the small test workbook.

resolve_bank(bank, parties, invoices) -> bank table with the three resolver columns

score_pairs(kind, ds, period=None, artifacts_dir=None) -> list[MatchResult]
# kind is "booking" or "payment". One MatchResult per invoice.

is_valid_gstin(text) -> bool
```

```python
class MatchResult(BaseModel):
    kind: "booking" | "payment" | "gstr2b"
    invoice_id: str
    right_id: str | None      # ledger entry_id or bank txn_id; None when unmatched
    confidence: float         # 0 to 1
    band: "auto" | "review" | "unmatched"
    reasons: list[str]        # up to 3 plain sentences
    features: dict[str, float]
```

Added with section 7:

```python
score_anomalies(ds, period=None) -> list[AnomalyResult]

class AnomalyResult(BaseModel):
    entity_type: "INVOICE" | "BANK_TRANSACTION"
    entity_id: str
    rule: str | None          # rule name, or None if only the forest flagged it
    score: float              # higher is more unusual
    reasons: list[str]
```

If a model file is missing, score_pairs raises ModelNotTrainedError and the message names the command that fixes it. It never returns an empty list in silence.

### 9.2 Commands

Run from the project folder. On Windows put ml\.venv\Scripts\ before python.

| Command | What it does |
|---|---|
| python -m ledgerlens_ml profile | checks the hash and columns, prints the facts in 3.3, the pair check in 5.1 and a summary of the features |
| python -m ledgerlens_ml augment | writes the three files in data/derived |
| python -m ledgerlens_ml train --model booking | trains the booking matcher, writes the model and card |
| python -m ledgerlens_ml train --model payment | trains the payment matcher |
| python -m ledgerlens_ml train --all | trains every model |
| python -m pytest ml/tests -q | runs the tests |
| python -m ledgerlens_ml train --model anomaly | fits the anomaly detector |
| python -m ledgerlens_ml evaluate | scores the test split, writes ml/reports/ML_REPORT.md and metrics.json |
| python -m ledgerlens_ml predict --period 2025-09 --out out/predictions_2025-09.json | runs every model on one month |
| python -m ledgerlens_ml train --model gstr2b | trains matcher D |

ML_REPORT.md layout: first a table of target against actual with pass or miss, then details per model, then the baseline comparison, then the known limits (including the Rule 37 clash in 3.4).

## 10. Tests

Write the test first, see it fail, then write the code. Test the logic, not the plumbing.

| Test file | What it checks |
|---|---|
| test_normalise.py | every row of the table in 4.1; party names on 6 real pairs; narration references |
| test_parties.py | the right Party for 10 real bank lines, including a cut-off name, a name without spaces and a line where only the narration helps |
| test_candidates.py | at least 99.5 percent of true pairs kept; no DEBIT paired with a sales invoice; the cap keeps the closest amounts |
| test_features.py | amounts, dates and ID features on hand-made pairs; column order equals config |
| test_split.py | no invoice in two splits; averages read train months only |
| test_matcher_contract.py | a saved model loads back; a changed feature list is refused; Confidence is 0 to 1; Band follows the thresholds; assignment is one to one |
| test_augment.py | two runs give identical files; rates within 1 percent of the settings; every GSTIN passes the check character |
| test_anomaly_rules.py | each rule fires on a planted row and stays quiet on a near miss |

ml/tests/fixtures/mini.xlsx is a small copy of the workbook: every record of 3 Suppliers and 3 Customers picked with seed 7 (280 invoices). ml/tests/fixtures/make_mini.py makes it. Most tests use it. test_augment.py loads the real workbook once (about 7 seconds) because the rates only mean something at full size. The whole suite should run in well under a minute.

## 11. Build order

Each step ends with something you can run. Run the tests after every step.

| Step | Build | Done when |
|---|---|---|
| 1 | package, requirements, config, data.py | profile runs and the hash check passes |
| 2 | augment.py | two runs give the same files |
| 3 | normalise.py, parties.py | the 4.1 table and the Party tests pass |
| 4 | candidates.py | the 99.5 percent check passes on train |
| 5 | features.py | feature tables build with empty values only in id_ratio and id_dl_sim |
| 6 | matcher.py, booking | card written, test numbers printed |
| 7 | payment matcher | card written |
| 8 | anomaly.py: rules, then the forest | card written, recall per rule printed |
| 9 | evaluate.py | ML_REPORT.md exists with the targets table |
| 10 | predict command | a predictions file for 2025-09 is written |
| 11 | matcher D | gstr2b card written |
| 12 | Benford screen | chart data in the predictions file |

## 12. Single-file program (optional)

For a laptop without Python you can build one Windows program:

```
ml\.venv\Scripts\python -m pip install pyinstaller==6.22.3
ml\.venv\Scripts\pyinstaller --onefile --name ledgerlens-ml --collect-data ledgerlens_ml --add-data "ml\artifacts;ledgerlens_ml\artifacts" ml\ledgerlens_ml\__main__.py
```

The result is dist\ledgerlens-ml.exe, roughly 60 to 120 MB. The app does not need it.

## 13. What can go wrong

| Risk | How you notice | What to do |
|---|---|---|
| The model barely beats the baseline | the card after training | ship the baseline; the code does this by itself |
| Fewer than 99.5 percent of true pairs are kept | the profile output | widen the date windows, raise the cap to 40 |
| The GSTR-2B lines are too clean | every line matched on the first try | raise the rates in config.py, run augment and train again |
| Anomaly precision is very low | the anomaly card | show only the rule flags, use the forest score for sorting |
| Someone asks why unpaid invoices marked benign are reported | questions | the Rule 37 note in 3.4 |
| A different Python on another laptop | pip install fails | use the saved files in ml/artifacts, or the program in section 12 |

## 14. Decisions and why

- Gradient boosting, not logistic regression: a near-match ID with an exact amount is strong, but each alone is weak. Trees learn such combinations. Logistic regression would need them hand-built.
- Calibrated scores: the score is shown to people as how sure we are, and it sets the Band. So it must behave like a probability.
- Split by time, not at random: a random split lets the model see later months of the same Party and makes the numbers look better than they are.
- One payment for several invoices is solved by exact search, not by the model: it is an exact sum problem, and a wrong learned answer would be hard to explain.
- The account step in Party resolution: same-named parties exist, and each Party has its own bank account.
- Benford is for the whole Company only, with no verdict until the cut-offs are checked.

## 15. Exporting the model and handing it over

The model is exported the moment training finishes: train writes the files in section 5.6 (and 7.4) into ml/artifacts. Nothing else needs converting.

Check the export before you hand it over:

1. Delete ml/artifacts, run train --all, and see the files come back.
2. Run the tests. All must pass.
3. Open each card.json. The targets table should say pass, or the report must explain the miss.
4. In Python, run this and see matches with reasons:

```python
from ledgerlens_ml import load_dataset, score_pairs
ds = load_dataset()
results = score_pairs("payment", ds, period="2025-09")
print(len(results), results[0])
```

Hand over these, as one zip:

- the whole ml folder, without ml/.venv (code, tests, artifacts, reports),
- data/derived (gstr2b.csv, augment_labels.csv, augment_manifest.json).

The app loads the model through the functions in section 9.1. So these must stay exactly as written here, or the app cannot use the model:

- the function names and arguments in 9.1, and the fields of MatchResult,
- the keys of the saved dict in 5.6 and the file names in ml/artifacts,
- the feature names and their order in 5.2,
- the column names in gstr2b.csv and augment_labels.csv,
- the package versions in 1.2 (a model saved with one scikit-learn version may not load in another).

Everything else is yours to change: the model settings, the windows, extra features (add them at the end of the list and retrain), the thresholds.
