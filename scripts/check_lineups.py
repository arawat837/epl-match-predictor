"""Gate L for the v2 lineup plan (docs/v2_lineup_plan.md): link the cached API-Football fixtures to
matches.parquet, build the lineup features and run the leakage checks. Nothing is scored.

Reads only the raw cache (no API requests). Seasons before the 2025-26 holdout only: later seasons
need the plan's development and verdict loaders, which are not built yet. Writes
data/processed/lineup_features.parquet (gitignored) and reports/v2_lineup_checks.csv (check counts
only, no API data). Exits 1 if under 99% of fixtures link or the real code is flagged anywhere.
Run from the project root: python -m scripts.check_lineups [--seasons 2024 2023 2022]
"""

import argparse
import sys

from src.config import PROCESSED_DIR, REPORTS_DIR, HOLDOUT_SEASON
from src.lineup_features import FEATURES, build_lineup_features
from src.lineup_leaks import lineup_check_report, lineup_matches, real_code_flags
from src.lineups import LINK_THRESHOLD, link_fixtures, link_rate, load_fixtures, load_lineups, match_lineups
from src.seasons import season_label, season_start
from src.splits import load_evaluation_matches

FEATURES_PATH = PROCESSED_DIR / "lineup_features.parquet"
REPORT_PATH = REPORTS_DIR / "v2_lineup_checks.csv"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2023, 2022])
    seasons = parser.parse_args(argv).seasons
    if max(seasons) >= season_start(HOLDOUT_SEASON):
        print(f"Seasons from {HOLDOUT_SEASON} on are not checked here yet (holdout and verdict seasons).")
        return 2
    matches = load_evaluation_matches()
    linked = link_fixtures(load_fixtures(seasons), matches)
    unlinked = linked[linked["match"].isna()]
    print(f"Fixtures: {len(linked)} in {', '.join(map(season_label, seasons))}; linked {link_rate(linked):.2%}.")
    for row in unlinked.itertuples():
        print(f"  unlinked: {row.date.date()} {row.home} v {row.away} (fixture {row.fixture_id})")
    lineups, incomplete = load_lineups(linked["fixture_id"])
    rows = match_lineups(lineups, linked)
    both = lineup_matches(rows)
    print(f"Lineups cached and complete: {len(both)} matches; incomplete: {len(incomplete)} {incomplete or ''}")
    features = build_lineup_features(matches, rows)
    FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.loc[both].to_parquet(FEATURES_PATH)
    print("Feature values present on those matches (home side): "
          + ", ".join(f"{name} {features.loc[both, f'home_{name}'].notna().sum()}" for name in FEATURES))
    report = lineup_check_report(matches, rows)
    print("\n" + report.to_string(index=False))
    report.to_csv(REPORT_PATH, index=False)
    print(f"\nwritten {REPORT_PATH} and {FEATURES_PATH}")
    return 0 if link_rate(linked) >= LINK_THRESHOLD and real_code_flags(report) == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
