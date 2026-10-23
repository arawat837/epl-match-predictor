"""Project-wide paths and constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MATCHES_PATH = PROCESSED_DIR / "matches.parquet"

FIRST_SEASON = 2005  # start year of 2005-06
MATCHES_PER_SEASON = 380
