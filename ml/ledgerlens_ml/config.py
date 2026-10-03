"""Seeds, windows, thresholds, split months and file paths. Constants only, no logic."""
from pathlib import Path

MODEL_VERSION = "2026.10.0"
SEED = 42

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "data" / "source" / "tax_recon_dataset.xlsx"
DATASET_SHA256 = "c49199eb35be2743ed9cdd9cf2db23996472c5194a01219fc49d01d0e084ab23"
DERIVED_DIR = REPO_ROOT / "data" / "derived"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"

# The workbook does not name the company.
COMPANY_NAME = "Sharma Traders Pvt Ltd"
COMPANY_GSTIN = "07AAACS1234F1ZU"
COMPANY_STATE_CODE = 7

FY_START = "2025-04-01"
FY_END = "2026-03-31"
DEMO_PERIOD = "2025-09"

TRAIN_MONTHS = ("2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12")
VALIDATION_MONTHS = ("2026-01",)
TEST_MONTHS = ("2026-02", "2026-03")

# Candidate windows in days, right date minus invoice date.
BOOKING_WINDOW = (-45, 75)
PAYMENT_WINDOW = (-45, 120)
CANDIDATE_CAP = 20
CANDIDATE_RECALL_GATE = 0.995
NAME_MATCH_MIN_SCORE = 88

BAND_AUTO = 0.90
BAND_REVIEW = 0.70
ASSIGNMENT_FLOOR = 0.30

HARD_CASE_LABELS = (
    "INVOICE_ID_MISMATCH",
    "AMOUNT_MISMATCH",
    "DATE_MISMATCH",
    "PAYMENT_AMOUNT_MISMATCH",
    "PAYMENT_BEFORE_INVOICE",
    "PARTIAL_PAYMENT",
    "BUNDLED_PAYMENT",
)

MATCHER_FEATURES_A = (
    "id_exact",
    "id_norm_exact",
    "id_serial_equal",
    "id_ratio",
    "id_dl_sim",
    "id_missing",
    "amt_rel_diff",
    "amt_within_1",
    "amt_ratio",
    "amt_log_left",
    "tax_rel_diff",
    "taxable_rel_diff",
    "date_diff_days",
    "date_abs_diff",
    "same_period",
    "party_score",
    "amt_rank",
    "date_rank",
    "n_candidates",
)

MATCHER_FEATURES_B = (
    "id_exact",
    "id_norm_exact",
    "id_serial_equal",
    "id_ratio",
    "id_dl_sim",
    "id_missing",
    "amt_rel_diff",
    "amt_within_1",
    "amt_ratio",
    "amt_log_left",
    "date_diff_days",
    "date_abs_diff",
    "party_score",
    "party_method_ref",
    "amt_rank",
    "date_rank",
    "n_candidates",
)

# GSTR-2B augmentation (ML_BUILD.md 3.5).
AUGMENT_FILING_BEHAVIOUR = (("reliable", 0.70), ("late", 0.20), ("non_filer", 0.10))
AUGMENT_ID_VARIANT_RATE = 0.30
AUGMENT_VALUE_MISMATCH_RATE = 0.03
AUGMENT_VALUE_MISMATCH_RANGE = (0.02, 0.15)
AUGMENT_DATE_SHIFT_RATE = 0.02
AUGMENT_DATE_SHIFT_DAYS = (1, 10)
AUGMENT_EXTRA_LINE_RATE = 0.02
AUGMENT_CANCELLED_SUPPLIERS = 2
RULE_37_DAYS = 180
