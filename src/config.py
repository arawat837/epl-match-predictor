"""Project-wide paths and constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MATCHES_PATH = PROCESSED_DIR / "matches.parquet"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
REPORTS_DIR = PROJECT_ROOT / "reports"

FIRST_SEASON = 2005  # start year of 2005-06
MATCHES_PER_SEASON = 380

FIRST_TEST_SEASON = "2015-16"  # first walk-forward test season
HOLDOUT_SEASON = "2025-26"  # final holdout; locked until the user releases it
