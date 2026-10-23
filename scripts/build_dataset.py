"""Download raw seasons, build data/processed/matches.parquet and print the quality report.

Run from the project root: python -m scripts.build_dataset
Exits with status 1 if any quality check fails.
"""

import sys

from src.data import build_matches, download_epl, save_matches
from src.quality import failed_checks, quality_report
from src.seasons import current_season, season_label


def main() -> int:
    matches = build_matches(download_epl())
    path = save_matches(matches)
    in_progress = season_label(current_season())
    print(f"Saved {len(matches)} matches to {path}\n")
    print(quality_report(matches, in_progress))
    return 1 if failed_checks(matches, in_progress) else 0


if __name__ == "__main__":
    sys.exit(main())
