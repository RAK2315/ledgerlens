# ML build spec: LedgerLens models

This file is the complete recipe for building, testing and shipping the LedgerLens machine learning models. A builder (human or agent) should be able to follow it top to bottom and end with trained model files, a metrics report and a command-line tool the backend can call, without asking questions.

Read CONTEXT.md first for vocabulary. Where this file and the deck disagree, this file wins for the build.

## 0. What is ML here, and what is not

LedgerLens follows one rule: code decides, AI explains. Every rupee figure comes from deterministic, tested code. The ML models only do two jobs where rules alone are brittle:

| Component | Type | Job | Ships in |
|---|---|---|---|
| A. Booking matcher | Supervised classifier | Scores how likely an invoice and a ledger booking are the same transaction | MVP |
| B. Payment matcher | Supervised classifier | Scores how likely an invoice and a bank transaction belong together | MVP |
| C. Anomaly detector | Rules plus Isolation Forest | Flags unusual invoices and bank flows, with a reason | MVP |
| D. Supplier filing matcher | Supervised classifier | Scores how likely a purchase invoice and a GSTR-2B line are the same supply | V2 (needs the GSTR-2B augmentation in section 3.5) |
| E. Benford screen | Statistical test | Company-level first-digit check | Stretch |

Not ML, and out of scope for this file: tax rule checks (rate, tax type, arithmetic, Rule 37, Section 17(5)), duplicate rules, one-to-many payment search (deterministic subset-sum), liability maths, and the Claude explainer. Those live in the backend engine. The models here return scores and reasons; the engine turns them into findings.

## 1. Requirements

### 1.1 Machine

- Windows 11, macOS or Linux, 8 GB RAM is enough. No GPU. Full training run takes under 5 minutes on a laptop.
- Python 3.10.11 exactly (the version on the build laptop). Python 3.11 or 3.12 also work with the same pins except networkx, see note below.
- Git.

### 1.2 Pinned packages

Create ml/requirements.txt with exactly this content. These are the newest releases that install on Python 3.10, checked with pip index on 2026-10-03.

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

Optional, only for the single-file executable in section 11:

```
pyinstaller==6.22.3
```

Note: networkx 3.5 and later need Python 3.11. Stay on 3.4.2 while the build runs on 3.10.

Why these and not others:

- scikit-learn HistGradientBoostingClassifier instead of LightGBM or XGBoost: same accuracy class for tabular data of this size, no extra native dependency to install on demo laptops, and it handles missing values natively.
- rapidfuzz for string similarity: fast C implementation, MIT licence, gives Levenshtein, Damerau-Levenshtein and token-set ratios in one package.
- No deep learning. The data is a few thousand tabular rows; a neural network would be slower to train, harder to explain and no more accurate.

### 1.3 Setup commands

From the repo root, PowerShell:

```
python -m venv ml\.venv
ml\.venv\Scripts\python -m pip install --upgrade pip
ml\.venv\Scripts\python -m pip install -r ml\requirements.txt
ml\.venv\Scripts\python -m pip install -e ml
```

Bash (macOS, Linux, Git Bash):

```
python -m venv ml/.venv
ml/.venv/bin/python -m pip install --upgrade pip   # Windows Git Bash: ml/.venv/Scripts/python
ml/.venv/bin/python -m pip install -r ml/requirements.txt
ml/.venv/bin/python -m pip install -e ml
```

ml/pyproject.toml declares the package name ledgerlens_ml, Python requires ">=3.10,<3.13", and no runtime dependencies beyond the requirements file.

## 2. Repo layout for the ML package

```
ml/
  pyproject.toml
  requirements.txt
  ledgerlens_ml/
    __init__.py          public API: load_dataset, score_pairs, score_anomalies, MODEL_VERSION
    config.py            seeds, windows, thresholds, split months, file paths
    data.py              load and validate the workbook, convert to typed frames
    augment.py           generate the GSTR-2B sheet and extra labels (section 3.5)
    normalise.py         invoice ID, party name, amount and date normalisers
    parties.py           resolve bank counterparties to party_id
    candidates.py        candidate pair generation (blocking) for each matcher
    features.py          pair features and anomaly features
    matcher.py           train, calibrate, save, load and score a matcher
    anomaly.py           rule detectors and Isolation Forest
    benford.py           stretch: company-level first-digit test
    evaluate.py          metrics against labels, writes the report
    cli.py               python -m ledgerlens_ml ... entry points
    __main__.py          dispatches to cli
  tests/
    test_normalise.py
    test_parties.py
    test_candidates.py
    test_features.py
    test_split.py
    test_matcher_contract.py
    test_anomaly_rules.py
    test_augment.py
  artifacts/             written by training, committed for the demo
  reports/               written by evaluation, committed
```

Seams, and why they exist:

- data.py is the only module that reads the workbook. Everything else receives typed DataFrames. This keeps the column contract in one place, so a renamed column breaks one function, not ten.
- features.py is pure: frames in, feature frame out, no file or model access. That makes every feature unit-testable and identical between training and inference.
- matcher.py and anomaly.py own model objects. No other module calls scikit-learn directly. If we swap the model type later, only these files change.
- The backend imports only from ledgerlens_ml/__init__.py. Internal modules can change freely.

## 3. Dataset of choice

### 3.1 The file

- Path: data/source/tax_recon_dataset.xlsx (committed to the repo).
- SHA-256: c49199eb35be2743ed9cdd9cf2db23996472c5194a01219fc49d01d0e084ab23
- data.py must check the hash on load and fail loudly if it differs, so a model card always names the exact data it was trained on.
- What it is: one financial year (2025-04-01 to 2026-03-31) of books for a fictional Delhi trading company (state code 07), with errors planted on purpose and an answer key. All 120 party GSTINs pass the check-digit test.
- Why this dataset: it is the only candidate that has all four record types linked by ground truth, an effective-dated tax rate table that includes the GST 2.0 change of 22 Sep 2025, and benign traps that let us measure false alarms. Alternatives checked and rejected on 2026-10-03: github.com/AnujSureshkumar/synthetic-finance-data (60 invoices, too small; we borrow only its GSTR-2B JSON shape), github.com/R3n0va/synthetic-accounting-data-generator (German VAT, not GST).

The demo company is Sharma Traders Pvt Ltd, GSTIN 07AAACS1234F1ZU (valid check digit). The workbook does not name the company; config.py sets these two values.

### 3.2 Sheets and column contract

data.py loads each sheet with these exact columns and types. Unknown extra columns are an error.

| Sheet | Rows | Columns (type) | Used for |
|---|---|---|---|
| invoices | 5,197 | invoice_id (str), doc_type (INVOICE, CREDIT_NOTE), invoice_type (SALES, PURCHASE), invoice_date (date), due_date (date), party_id (str), party_name (str), party_gstin (str), party_state_code (int), place_of_supply (int), hsn_sac (int), category (str), taxable_value (float), tax_rate_pct (int), cgst, sgst, igst, total_tax, invoice_total (float), currency (str), original_invoice_id (str, nullable) | Left side of every matcher, anomaly features |
| bank_transactions | 4,690 | txn_id, txn_date (date), value_date (date), bank_account, direction (DEBIT, CREDIT), amount (float), currency, counterparty_name, counterparty_account, payment_mode (CHEQUE, NEFT, RTGS, IMPS, UPI), utr, narration (str), closing_balance (float) | Right side of payment matcher, circular-flow rule |
| accounting_ledger | 9,948 | entry_id, voucher_no, posting_date (date), fiscal_period (YYYY-MM), voucher_type (SALES, PURCHASE, PAYMENT, RECEIPT, CREDIT_NOTE, JOURNAL, TAX_PAYMENT), ledger_account, party_id, party_name, invoice_ref (str, nullable), taxable_amount, cgst, sgst, igst, total_tax, total_amount, debit, credit (float), utr_ref (nullable), narration, entered_by, entry_timestamp | Right side of booking matcher |
| tax_rates | 15 | category_code, category, hsn_sac (int), supply_type, gst_rate_pct, cgst_pct, sgst_pct, igst_pct, effective_from (date), effective_to (date, nullable), is_exempt (bool) | Expected-rate feature, effective-dated |
| party_master | 120 | party_id, party_name, party_type (CUSTOMER 70, VENDOR 50), gstin, pan, state_code, state, payment_terms_days | Party resolution, PAN links |
| tax_filings | 12 | period, return_type, due_date, filing_date, outward_taxable_value, output_cgst, output_sgst, output_igst, total_output_tax, itc_cgst, itc_sgst, itc_igst, total_itc_claimed, net_tax_payable, status | Not used by ML (engine uses it) |
| answer_key | 12 | period, true_outward_taxable_value, true_output_tax, true_eligible_itc, itc_blocked_invalid_supplier_gstin, true_net_tax_liability, declared_total_output_tax, declared_total_itc, declared_net_tax_payable, liability_gap_inr | Not used by ML (engine tests use it) |
| labels | 2,149 | issue_id, issue_type, issue_category, severity, entity_type (INVOICE, BANK_TRANSACTION, LEDGER_ENTRY, TAX_FILING), entity_id, related_entity_id (nullable), field_affected, expected_value, recorded_value, financial_impact_inr, description, is_benign (bool) | Evaluation, and hard-case weighting |
| links | 5,519 | invoice_id, booking_entry_id (nullable, 43 null), txn_id (nullable, 819 null), receipt_entry_id (nullable), allocated_amount (float), link_type (FULL 3,898, UNPAID_OPEN 722, PARTIAL 629, BUNDLED 180, CREDIT_NOTE 60, DUPLICATE_INVOICE_UNPAID 17, DUPLICATE_PAYMENT_EXCESS 13) | Training labels for matchers A and B |

All money is converted to integer paise in data.py (round half up). All dates become datetime64 at day precision. IDs are kept raw; normalised forms live in separate columns.

### 3.3 Facts measured on this file (2026-10-03)

These shaped the design. Re-measure in the data profile step and update this table if anything differs.

- Purchase invoices per month: 144 to 217. Median 43 purchase invoices per vendor.
- 67.8 percent of bank narrations quote the invoice ID as written (VEN001-0001, INV VEN002-0001); 24.9 percent quote it in another form (ven0420001, inv252601229, or the serial alone such as 0035); 7.3 percent carry no reference.
- 76.6 percent of bank counterparty names exactly equal a party_master name; the rest are truncated to 22 characters, written without spaces (BHARATSYSTEMSPVTLTD) or shortened (PRIME MEDIA).
- 22 parties share a normalised name with another party (Evergreen Infra & Co and Evergreen Infra Private Limited), so a name alone cannot always pick the party. Every party uses exactly one counterparty_account, and no account is shared.
- 99.5 percent of ledger invoice_ref values exist in invoices; the rest are planted typos.
- Candidate recall on train (section 5.1 gate): booking 100.0 percent of 3,852 true pairs, payment 100.0 percent of 3,976.
- Counterparty resolution (section 4.2) is correct on 100.0 percent of linked bank transactions; without the account step it is 98.6 percent.
- Planted ledger ID typos include a wrong financial year (INV-2425-02759 for INV-2526-02759), letter O for zero (INV-2526-O2328), swapped digits (01978 for 01987) and dropped digits (INV-252-02921).
- Payment lag from invoice date: minimum minus 30 days (planted payment-before-invoice), 5th percentile 4, median 25, 95th percentile 55, maximum 101 days.
- For FULL links, payment amount divided by invoice total: median 1.0, minimum 0.903, maximum 1.048.
- At most 2 bank transactions per invoice (partial payments) and at most 2 invoices per bank transaction (bundled payments).

### 3.4 Labels: what counts as truth

- Matchers A and B: a pair (invoice, ledger entry) is positive if links has that invoice_id with that booking_entry_id. A pair (invoice, bank transaction) is positive if links has that invoice_id with that txn_id. Every other candidate pair is negative.
- Anomaly detector: unsupervised. Labels with issue_category ANOMALY are used only to choose thresholds on validation and to report recall and precision on test.
- Benign traps (is_benign true: BUNDLED_PAYMENT, CREDIT_NOTE, LEGIT_OPEN_INVOICE, NON_INVOICE_TXN, PARTIAL_PAYMENT, ROUNDING_NOISE) must not produce a finding. Any finding on a benign-trap entity counts as a false alarm in the report.
- Known conflict to handle, not hide: an open purchase invoice older than 180 days is labelled LEGIT_OPEN_INVOICE in the workbook, but under Rule 37 it is a real ITC risk. The engine reports it as a Rule 37 finding; evaluate.py scores Rule 37 against the augmentation labels (section 3.5) and excludes those entities from the benign false-alarm count. Write this in the report so nobody thinks we are gaming the metric.

### 3.5 Augmentation: GSTR-2B and extra labels

The workbook has no supplier filing data, but the core USP (ITC at risk and ITC found) needs it. augment.py generates it, deterministically, seed 42.

Command: python -m ledgerlens_ml augment

Writes data/derived/gstr2b.csv, data/derived/augment_labels.csv, and data/derived/augment_manifest.json (seed, rates, source hash, row counts).

Steps, in order:

1. Assign each of the 50 vendors a filing behaviour: reliable 70 percent, late 20 percent, non_filer 10 percent, chosen with numpy default_rng(42) over vendors sorted by party_id.
2. For each PURCHASE invoice with doc_type INVOICE:
   - reliable: one GSTR-2B line in the same return period (invoice month).
   - late: one line in the next month's period.
   - non_filer: no line. Label MISSING_IN_2B with financial_impact = total_tax.
3. Supplier-side variation on generated lines, each drawn independently:
   - 30 percent: invoice number written in a supplier format: digits only (VEN001-0001 becomes 1), slash form (VEN/001/0001), or INV prefix (INV-0001). Not an error; the matcher must still match.
   - 3 percent: taxable value differs by 2 to 15 percent. Label GSTR2B_VALUE_MISMATCH with impact = tax difference.
   - 2 percent: invoice date shifted by 1 to 10 days. Not an error unless it crosses a month boundary, then label PERIOD_SHIFT.
4. Add GSTR-2B-only lines equal to 2 percent of purchase invoices: plausible supplies from existing vendors with fresh invoice numbers that are absent from the books. Label MISSING_IN_BOOKS with impact = tax (this is ITC found).
5. Rule 37: every PURCHASE invoice whose links row is UNPAID_OPEN and whose invoice date is more than 180 days before 2026-03-31 gets a label RULE_37_UNPAID_180 with impact = total_tax.
6. Cancelled suppliers: mark 2 vendors (the two non_filers with the most invoices) as GSTIN cancelled from a date in the middle of their invoices. Invoices dated after that get CANCELLED_GSTIN labels.
7. PAN rings: pick one vendor and one customer, and rewrite the customer's PAN and GSTIN characters 3 to 12 to equal the vendor's PAN, recomputing the check digit. Label both PAN_LINKED_RING. This is the round-trip shown in the deck.

GSTR-2B columns (mirror the GSTN B2B section; verify field names against the official GSTR-2B JSON schema before the demo and adjust names only): gstin_supplier, trade_name, invoice_number, invoice_type (R), invoice_date, invoice_value, place_of_supply, reverse_charge (N), rate, taxable_value, igst, cgst, sgst, cess, return_period (MMYYYY), itc_availability (Y, N), reason (nullable), source_invoice_id (hidden from the engine; used only by evaluation).

augment_labels.csv has the same columns as the labels sheet plus source = augment, so evaluate.py treats both label sources the same way.

Choices made while building augment.py (the steps above left them open):

- Filing behaviour is an exact split (35 reliable, 10 late, 5 non_filer) by a seeded shuffle, not independent draws. The ring supplier is held reliable so the ring is not confused with a missing line.
- A purchase invoice labelled DUPLICATE_INVOICE in the workbook gets no GSTR-2B line and no MISSING_IN_2B label: the supplier issued it once. The engine must report it as a duplicate only.
- Every line of a late supplier is labelled PERIOD_SHIFT, as is a reliable supplier's line whose shifted date crosses a month. Date shifts go forward only and the return period is never more than one month after the invoice month, so the supplier-filing candidates (invoice month or the next) always reach the line.
- gstr2b.csv carries a line_id column (2B-000001 onwards) and money in rupees with two decimals; data.py converts to paise on load.
- New entity_type values: GSTR2B_LINE (MISSING_IN_BOOKS, entity_id is the line_id) and PARTY (PAN_LINKED_RING, entity_id is the party_id, related_entity_id the other party).
- The ring supplier is the supplier behind the earliest CIRCULAR_FLOW label, so the ring has a round trip to show; the customer is a seeded pick. With seed 42: supplier VEN-009 Unity Infra Pvt Ltd (Rs 5,00,000 out on 30 Sep 2025, back on 2 Oct 2025) and customer CUS-007 Unity Motors Ltd.
- Cancelled suppliers with seed 42: VEN-006 from 2025-09-02 and VEN-010 from 2025-10-29 (the date of each supplier's middle invoice).
- data.load_dataset applies the manifest: party frames gain filing_behaviour, gstin_status and cancelled_from; the ring customer's PAN and GSTIN change in the party frame and on its invoices (planted invalid GSTINs on invoices are left alone).
- Counts with seed 42: 1,931 lines (42 of them absent from the books); labels MISSING_IN_2B 220, PERIOD_SHIFT 415, GSTR2B_VALUE_MISMATCH 51, MISSING_IN_BOOKS 42, RULE_37_UNPAID_180 35, CANCELLED_GSTIN 51, PAN_LINKED_RING 2.

### 3.6 Splits

Temporal, by invoice date, because the real product will always be scoring a month it has never seen:

| Split | Months | Purpose |
|---|---|---|
| train | 2025-04 to 2025-12 | fit models |
| validation | 2026-01 | choose thresholds, early stopping, calibration check |
| test | 2026-02 to 2026-03 | final numbers in the report; touched once per release |

Rules: a candidate pair belongs to the split of its invoice. Party medians and other aggregate features are computed from train months only and frozen into the artifact. test_split.py asserts no invoice ID appears in two splits and no aggregate feature reads test rows.

The demo month, September 2025, sits inside train. That is fine for a demo but the report must quote test-split numbers, never demo-month numbers.

## 4. Shared preprocessing (normalise.py, parties.py)

### 4.1 Invoice ID normaliser

normalise_invoice_id(raw: str) -> str, applied identically to invoices.invoice_id, ledger invoice_ref, tokens from bank narrations and GSTR-2B invoice_number:

1. Uppercase, strip whitespace.
2. Map look-alike letters in digit positions: O to 0, I and L to 1, S to 5, only when the character sits between two digits or at the start of a digit run.
3. Remove leading document prefixes: INV, BILL, NO, TAX INVOICE, followed by optional separators.
4. Remove separators: slash, hyphen, underscore, dot, space.
5. Remove one financial-year token when the remaining string still has at least 3 digits: 2526, 2425, FY26, FY2526, 25-26 (already de-separated to 2526).
6. Strip leading zeros from the final numeric run only.

Keep the raw value too. Also expose id_serial(raw) -> str: the final numeric run without leading zeros.

Test cases (write these first, all must pass):

| Input | normalise_invoice_id | id_serial |
|---|---|---|
| INV-2526-02759 | 2759 | 2759 |
| INV-2425-02759 | 2759 | 2759 |
| INV-2526-O2328 | 2328 | 2328 |
| INV-252-02921 | 2522921 or 2921, see note | 2921 |
| VEN042-0001 | VEN0421 | 1 |
| ven0420001 | VEN0421 | 1 |
| INV VEN002-0001 | VEN0021 | 1 |
| VEN/001/0001 | VEN0011 | 1 |

Note on INV-252-02921: 252 is not a valid year token, so it stays and the normalised forms differ. That is intended; the fuzzy features (4.3) catch it. The test asserts id_serial equality and a Damerau-Levenshtein distance of 1 on the raw strings.

Implementation detail for VEN codes: strip leading zeros from the final numeric run only, so VEN042-0001 becomes VEN042 + 1 = VEN0421. The vendor prefix keeps its zeros because it is not the final run.

### 4.2 Party name normaliser and resolution

normalise_party_name(raw) -> str: uppercase, replace & with AND, remove PVT, PRIVATE, LTD, LIMITED, LLP, CO, AND CO, punctuation, collapse spaces.

PartyResolver.resolve(name, narration, direction, account) -> (party_id or None, score, method); resolve_bank(bank, parties, invoices) runs it over the whole statement and adds resolved_party_id, resolve_score and resolve_method:

1. If the narration contains a token whose normalised form equals a normalised invoice_id, return that invoice's party_id with score 100, method invoice_ref. Only purchase invoices are considered for a DEBIT and sales invoices for a CREDIT, because a bare supplier serial (0035) would otherwise read as sales invoice 35.
2. Else if the counterparty_account was seen on rows resolved by step 1, return the party those rows point to, score 100, method account. Added during the build: same-named parties make the name step wrong on 12 percent of the rows it handles.
3. Else the best normalised name by the higher of token_set_ratio and the ratio with spaces removed; ties go to the party type that fits the direction, then to the closer legal suffix. Accept if the score is at least 88, method name.
4. Else None.

A name scoring 95 or more overrides an invoice reference that points at a different party, unless the account agrees with the reference (a mistyped reference is likelier than a wrong name).

Party resolution runs before candidate generation for the payment matcher. Its accuracy against links-derived truth is reported separately in the report.

### 4.3 String similarity primitives

From rapidfuzz: fuzz.ratio, fuzz.partial_ratio, fuzz.token_set_ratio, distance.DamerauLevenshtein.normalized_similarity. All return 0 to 100 or 0 to 1; features store them as floats in 0 to 1.

## 5. Matchers A and B (booking and payment)

### 5.1 Candidate generation (candidates.py)

Booking matcher A, for each invoice:
- Ledger entries with voucher_type PURCHASE when invoice_type is PURCHASE, SALES when SALES, CREDIT_NOTE when doc_type is CREDIT_NOTE.
- Same party_id.
- posting_date within minus 45 to plus 75 days of invoice_date.
- Cap: keep the 20 candidates with the smallest absolute amount difference.

Payment matcher B, for each invoice:
- Bank direction DEBIT for PURCHASE, CREDIT for SALES.
- Resolved party_id equals the invoice's party_id, or the narration contains the invoice's normalised ID.
- txn_date within minus 45 to plus 120 days of invoice_date.
- Cap: 20 by smallest absolute amount difference, but always keep any candidate whose narration contains the invoice ID.

Recall check, a hard gate: on train, at least 99.5 percent of true pairs from links must survive candidate generation. If not, widen windows before training. test_candidates.py asserts this on a fixed fixture.

### 5.2 Features (features.py)

One row per candidate pair. All numeric, missing values allowed (HistGradientBoosting handles NaN).

| Feature | Definition | A | B |
|---|---|---|---|
| id_exact | raw IDs equal (1, 0) | yes | narration contains raw ID |
| id_norm_exact | normalised IDs equal | yes | narration token normalised equal |
| id_serial_equal | id_serial equal | yes | yes |
| id_ratio | fuzz.ratio on normalised IDs, 0 to 1 | yes | best over narration tokens |
| id_dl_sim | Damerau-Levenshtein normalized similarity on raw uppercase IDs | yes | best over narration tokens |
| id_missing | right side has no ID (1, 0) | yes | yes |
| amt_rel_diff | abs(left minus right) divided by max(left, right), on totals in paise | yes | yes |
| amt_within_1 | abs difference at most 100 paise | yes | yes |
| amt_ratio | right divided by left | yes | yes |
| amt_log_left | log10 of invoice total in rupees | yes | yes |
| tax_rel_diff | same as amt_rel_diff on total_tax | yes | no |
| taxable_rel_diff | same on taxable value | yes | no |
| date_diff_days | right date minus invoice date, signed | yes | yes |
| date_abs_diff | absolute value of the above | yes | yes |
| same_period | same YYYY-MM | yes | no |
| party_score | 1.0 for same party_id in A; resolver score divided by 100 in B | yes | yes |
| party_method_ref | resolver used invoice_ref (1, 0) | no | yes |
| amt_rank | rank of amt_rel_diff among this invoice's candidates, 1 is closest | yes | yes |
| date_rank | rank of date_abs_diff among this invoice's candidates | yes | yes |
| n_candidates | candidate count for this invoice | yes | yes |
| right_open_amount_ratio | for B: bank amount divided by invoice amount still unallocated after higher-ranked matches (computed in a second pass, set NaN in first pass) | no | V2 |

Feature list order is fixed in config.py as MATCHER_FEATURES_A and MATCHER_FEATURES_B and saved into the model card. Inference refuses to run if the artifact's feature list differs from the code's.

### 5.3 Model and training (matcher.py)

```
HistGradientBoostingClassifier(
    learning_rate=0.08,
    max_iter=400,
    max_leaf_nodes=31,
    min_samples_leaf=20,
    l2_regularization=1.0,
    early_stopping=False,       # we stop on the validation month ourselves, see step 3
    warm_start=True,
    class_weight="balanced",
    random_state=42,
)
```

Training procedure:

1. Build candidates and features for train and validation.
2. Sample weights: weight 3.0 for positive pairs whose invoice or ledger entry carries a hard-case label (INVOICE_ID_MISMATCH, AMOUNT_MISMATCH, DATE_MISMATCH, PAYMENT_AMOUNT_MISMATCH, PAYMENT_BEFORE_INVOICE, PARTIAL_PAYMENT, BUNDLED_PAYMENT), 1.0 otherwise. Reason: these are rare and they are exactly what the demo shows.
3. Fit on train in a loop: set max_iter to 20, 40, 60 and so on up to 400, calling fit each time (warm_start keeps earlier trees). After each step compute average precision on the validation month. Stop after 3 steps without improvement and refit to the best iteration count.
4. Calibrate on the validation month: CalibratedClassifierCV(FrozenEstimator(fitted_model), method="isotonic") then fit(X_val, y_val). FrozenEstimator comes from sklearn.frozen; the older cv="prefit" form is deprecated in scikit-learn 1.7. The calibrated probability is the confidence shown in the UI.
5. Baseline: a rule score, 0.45 x id_dl_sim + 0.30 x (1 minus min(amt_rel_diff x 10, 1)) + 0.15 x (1 minus min(date_abs_diff / 60, 1)) + 0.10 x party_score. Report it next to the model. Ship the model only if its test F1 beats the baseline by at least 0.01; otherwise ship the baseline as the matcher (same interface) and say so in the report. This is the demo-safe fallback.

### 5.4 From scores to matches

Per party block, after scoring:

1. Assignment: scipy.optimize.linear_sum_assignment on cost 1 minus calibrated probability, over invoices x candidates in the block. Pairs below 0.30 are given cost 10 so they are never forced.
2. Bands: confidence at least 0.90 is auto-matched, 0.70 to 0.90 goes to the review queue, below 0.70 is unmatched. Put these numbers in config.py; tune them on validation for at most 1 percent false auto-matches.
3. Payment matcher only: after one-to-one assignment, leftover bank transactions and leftover invoice balances go to the deterministic one-to-many search in the backend (same party, 60-day window, at most 15 open invoices, exact subset-sum on paise within 100 paise tolerance, prefer fewest invoices then oldest). That search is not ML; it is listed here so the matcher does not try to learn it.
4. Every returned match carries reasons: the top 3 features by contribution. Use sklearn.inspection.permutation_importance once at training time to rank features globally, then at inference give plain reasons from feature values with fixed templates, for example "Invoice number matches after removing prefix and year", "Amount differs by Rs 1.40", "Paid 3 days after invoice". Templates live in matcher.py, one per feature.

### 5.5 Metrics and acceptance gates

Report on the test split:

- Pair level: precision, recall, F1 at the auto-match threshold, and average precision.
- Invoice level after assignment: share of invoices whose assigned partner equals links truth.
- Hard cases: recall on positive pairs carrying each hard-case label (5.3 step 2).
- Benign traps: share of PARTIAL_PAYMENT, BUNDLED_PAYMENT and ROUNDING_NOISE entities that end up matched rather than flagged.

Targets (targets, not claims; report the real numbers whatever they are):

| Metric | Booking A | Payment B |
|---|---|---|
| Pair F1 at auto threshold | 0.97 | 0.95 |
| Invoice-level link accuracy | 0.98 | 0.95 |
| Recall on INVOICE_ID_MISMATCH pairs | 0.90 | 0.85 |
| Benign traps matched, not flagged | 0.95 | 0.95 |
| False auto-matches (precision complement) | at most 1 percent | at most 1 percent |

If a target is missed, the report says so in its first lines. Never tune on test.

### 5.6 Artifacts

- ml/artifacts/matcher_booking.joblib and ml/artifacts/matcher_payment.joblib: a dict with keys model (calibrated estimator or the baseline marker), features (list), thresholds (auto, review), frozen_aggregates (dict), model_version, trained_at, data_sha256.
- ml/artifacts/matcher_booking.card.json and matcher_payment.card.json: the same metadata plus all metrics from 5.5, feature importances and the baseline comparison.

## 6. Matcher D (supplier filing, V2)

Same pipeline as 5, with:

- Left: PURCHASE invoices. Right: data/derived/gstr2b.csv lines.
- Candidates: same supplier GSTIN exactly (never fuzzy-match a GSTIN), return period equal to invoice month or the next month, cap 10.
- Extra features: period_offset (0 or 1), rate_equal, igst_vs_cgst_pattern_equal (both inter-state or both intra-state).
- Labels: source_invoice_id in gstr2b.csv. That column is dropped before features are built.
- Outputs feed the engine's MISSING_IN_2B, MISSING_IN_BOOKS and GSTR2B_VALUE_MISMATCH findings.
- Targets: pair F1 0.97; recall on supplier-format ID variants 0.95.
- Artifact: ml/artifacts/matcher_gstr2b.joblib plus card.

## 7. Anomaly detector C

Anomalies must come with a reason a finance judge accepts. So: explicit rule detectors for each known pattern, plus an Isolation Forest that catches what the rules miss and ranks severity. Each flag says which rule fired or which features drove the score.

### 7.1 Rule detectors (anomaly.py, deterministic)

| Rule | Fires when | Maps to label |
|---|---|---|
| outlier_amount | taxable value at least 10 times the party's train median, or at least 10 times the category median when the party has fewer than 5 train invoices | OUTLIER_AMOUNT |
| round_amount_spike | taxable value at least Rs 1,00,000 and divisible by Rs 10,000 | ROUND_AMOUNT_SPIKE |
| threshold_splitting | 3 or more invoices from one vendor within 4 days, each between 90 and 100 percent of the Rs 2,00,000 approval limit | THRESHOLD_SPLITTING |
| vendor_burst | 6 or more invoices from one vendor within 3 days, each below the vendor's train median | VENDOR_BURST |
| weekend_large | invoice dated Sunday and taxable value above the 95th percentile of train | WEEKEND_LARGE_TXN |
| circular_flow | a bank DEBIT to a party with an amount divisible by Rs 50,000 and no linked invoice, followed within 10 days by a CREDIT from the same resolved party of the same amount | CIRCULAR_FLOW |

The approval limit (Rs 2,00,000) and all constants live in config.py. Thresholds above are starting points; tune on validation, then freeze.

### 7.2 Isolation Forest

Fit on PURCHASE and SALES invoices in train months:

```
IsolationForest(n_estimators=300, max_samples="auto", contamination="auto", random_state=42)
```

Features: log10 taxable value, ratio to party train median, ratio to category train median, z-score within category, is_round_10000, day_of_week, is_sunday, day_of_month, invoices from same party in previous 3 days, invoices from same party in previous 7 days, days since party's first invoice, tax_rate_pct, is_interstate.

Score: score_samples, negated so higher is more unusual. Threshold: choose on validation the score at which precision against ANOMALY labels is at least 0.5, then freeze it. Explanation: for a flagged invoice, report the 2 features with the largest absolute z-score against the train distribution, with templates like "15 times this supplier's usual invoice" or "Dated on a Sunday".

### 7.3 Metrics and targets

Per anomaly label type on test: recall, precision, and number of flags. Overall false alarm rate on benign-trap entities. Targets: rule detectors recall 0.90 on their own label type; combined precision 0.50; benign false alarms at most 2 percent. Report real numbers.

### 7.4 Artifacts

ml/artifacts/anomaly_invoice.joblib (forest, features, frozen medians and percentiles, threshold, rule constants) and anomaly_invoice.card.json.

## 8. Benford screen E (stretch)

Company-level only: first-digit distribution of taxable values across all purchase invoices in the period, compared to Benford's expected proportions with mean absolute deviation (MAD). Do not run per vendor: median 43 invoices per vendor is too few. Before showing a verdict in the UI, verify the MAD conformity thresholds from a primary source and record it in docs/RESEARCH.md; until then show the chart with the label "screening only" and no pass or fail verdict.

## 9. Public API and command line

### 9.1 Python API (ledgerlens_ml/__init__.py)

```python
MODEL_VERSION: str  # for example "2026.10.0"

def load_dataset(path: str | None = None) -> Dataset: ...
    # Dataset is a frozen dataclass of typed DataFrames: invoices, bank, ledger, tax_rates,
    # parties, filings, answer_key, labels, links, gstr2b (None until augmented).

def score_pairs(kind: Literal["booking", "payment", "gstr2b"], ds: Dataset,
                period: str | None = None) -> list[MatchResult]: ...

def score_anomalies(ds: Dataset, period: str | None = None) -> list[AnomalyResult]: ...
```

```python
class MatchResult(BaseModel):          # pydantic v2
    kind: Literal["booking", "payment", "gstr2b"]
    invoice_id: str
    right_id: str | None               # ledger entry_id, bank txn_id or gstr2b line id
    confidence: float                  # calibrated, 0 to 1
    band: Literal["auto", "review", "unmatched"]
    reasons: list[str]                 # plain sentences, at most 3
    features: dict[str, float]         # for the diff view and debugging

class AnomalyResult(BaseModel):
    entity_type: Literal["INVOICE", "BANK_TRANSACTION"]
    entity_id: str
    rule: str | None                   # rule name from 7.1, or None if forest-only
    score: float                       # forest score, higher is more unusual
    reasons: list[str]
```

Failure behaviour: if an artifact is missing, score_pairs raises ModelNotTrainedError with the command to fix it. The backend catches it and falls back to the baseline rule score, showing "baseline matcher" in the UI. It never silently returns empty results.

### 9.2 Commands

All run from the repo root with the ml venv active (or prefix with ml\.venv\Scripts\python on Windows).

| Command | Does |
|---|---|
| python -m ledgerlens_ml profile | checks the hash and column contract, prints the facts table in 3.3 |
| python -m ledgerlens_ml augment | writes data/derived/gstr2b.csv and augment labels |
| python -m ledgerlens_ml train --model booking | trains matcher A, writes artifact and card |
| python -m ledgerlens_ml train --model payment | trains matcher B |
| python -m ledgerlens_ml train --model gstr2b | trains matcher D (V2) |
| python -m ledgerlens_ml train --model anomaly | fits detector C |
| python -m ledgerlens_ml train --all | all of the above in order |
| python -m ledgerlens_ml evaluate | scores test split, writes ml/reports/ML_REPORT.md and ml/reports/metrics.json |
| python -m ledgerlens_ml predict --period 2025-09 --out out/predictions_2025-09.json | runs every model on one month, writes MatchResult and AnomalyResult lists |
| python -m pytest ml/tests -q | unit tests |

ML_REPORT.md layout: first a table of targets vs actual with pass or miss, then per-model detail, then the baseline comparison, then known limitations (including the Rule 37 label conflict in 3.4).

## 10. Tests to write first (TDD)

Write each test, watch it fail, then implement. Do not write tests for glue or plotting.

| Test file | Asserts |
|---|---|
| test_normalise.py | every row of the table in 4.1; party name normaliser on 6 real pairs from the data |
| test_parties.py | resolver returns the right party for 10 hand-picked bank rows, including one truncated name and one narration-only case |
| test_candidates.py | candidate recall at least 99.5 percent on a 200-invoice fixture; no candidate crosses direction (DEBIT with SALES) |
| test_features.py | amt_rel_diff, date_diff_days and id features on hand-built pairs; feature column order equals config |
| test_split.py | no invoice in two splits; aggregates read train only |
| test_matcher_contract.py | saved artifact round-trips; inference rejects a mismatched feature list; confidence in 0 to 1; band follows thresholds |
| test_anomaly_rules.py | each rule fires on a planted fixture row and stays silent on a near miss |
| test_augment.py | same seed gives byte-identical gstr2b.csv; label counts within 1 percent of configured rates; every generated GSTIN passes the check digit |

A small fixture workbook (ml/tests/fixtures/mini.xlsx, written by ml/tests/fixtures/make_mini.py: every record of 3 suppliers and 3 customers picked with seed 7, 280 invoices) keeps most tests fast. test_augment.py loads the real workbook once (about 7 seconds) because the augmentation rates only mean something at full size; the whole suite runs in about 10 seconds.

## 11. Build order with done conditions

Each step ends with something you can run and check. Typecheck is not applicable to plain Python here; run python -m pytest ml/tests -q after every step.

| Step | Build | Done when | Verify with |
|---|---|---|---|
| 1 | Package skeleton, requirements, config, data.py with hash and column checks | profile prints the 3.3 facts and they match | python -m ledgerlens_ml profile |
| 1b | augment.py (tests first), because the MVP headline numbers (ITC at risk, ITC found) need GSTR-2B lines, matched by the baseline rule score until matcher D exists | gstr2b.csv and augment labels written, same bytes on rerun | augment, then pytest |
| 2 | normalise.py, parties.py (tests first) | all 4.1 cases and resolver tests pass | pytest |
| 3 | candidates.py (tests first) | candidate recall gate passes on full train | profile output adds candidate recall line |
| 4 | features.py (tests first) | feature frame builds for train, no NaN except where allowed | pytest, plus a printed describe() |
| 5 | matcher.py for booking: baseline, model, calibration, assignment, reasons | card written; test metrics printed | train --model booking |
| 6 | payment matcher | card written | train --model payment |
| 7 | anomaly.py rules then forest | card written; per-rule recall printed | train --model anomaly |
| 8 | evaluate.py and report | ML_REPORT.md exists with targets table | evaluate |
| 9 | predict command and API used by the backend | predictions JSON for 2025-09 loads in the backend | predict --period 2025-09 |
| 10 | learned gstr2b matcher (V2) | gstr2b card written | train --model gstr2b |
| 11 | Benford screen (stretch) | chart data in predictions JSON, labelled screening only | predict |

Something demo-able exists after step 6: the backend can show matched, review and unmatched pairs with confidence and reasons for any month.

## 12. Single-file executable (optional)

For a laptop without Python, build a Windows executable of the command line:

```
ml\.venv\Scripts\python -m pip install pyinstaller==6.22.3
ml\.venv\Scripts\pyinstaller --onefile --name ledgerlens-ml --collect-data ledgerlens_ml --add-data "ml\artifacts;ledgerlens_ml\artifacts" ml\ledgerlens_ml\__main__.py
```

Output: dist\ledgerlens-ml.exe. Check it with: dist\ledgerlens-ml.exe predict --period 2025-09 --out out\check.json. Expect a file of roughly 60 to 120 MB (numpy, scipy and scikit-learn are bundled). The demo itself does not need this; the backend imports the package directly.

## 13. Risks and fallbacks

| Risk | Early signal | Fallback that still demos |
|---|---|---|
| Model barely beats the rule baseline | step 5 report | ship the baseline matcher through the same interface; the deck says "rules with confidence scores" and it is still true |
| Candidate recall below 99.5 percent | step 3 gate | widen date windows, raise the cap to 40, add narration-ID candidates regardless of party |
| Augmented GSTR-2B looks too clean | ID-variant recall near 1.0 on day one | raise variant and value-mismatch rates in config, regenerate, retrain; never hand-edit the CSV |
| Anomaly precision very low | step 7 | show rule-based anomalies only, forest score as a secondary sort; say so in the report |
| Label conflict on Rule 37 confuses a judge | question in Q and A | the report section in 3.4 explains it in two sentences |
| Different Python on the demo laptop | pip install fails | use the committed artifacts plus the PyInstaller executable from section 12 |

## 14. Decisions made (override if you disagree)

- Gradient boosting over logistic regression: interactions between ID similarity and amount difference matter (a near-match ID with an exact amount is strong; either alone is weak). Logistic regression would need hand-built interaction features.
- Calibrated probabilities are shown to users as "how sure we are". Isotonic calibration on the validation month, because the score drives the auto, review and unmatched bands.
- Temporal split, not random: a random split leaks vendor-specific patterns from the future and inflates numbers.
- The one-to-many payment search stays deterministic: it is an exact combinatorial problem, and a wrong learned answer would be hard to explain.
- Benford is company-level only and verdict-free until thresholds are verified.
