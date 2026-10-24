"""Gate I, then Gate L, for the pre-lineup injury variant v2-pre (docs/v2_lineup_plan.md amendment A2).
Nothing is scored.

Reads only the raw cache (no API requests). Gate I: on fixtures with both a lineup and injury records,
at most 2% of "Missing Fixture" records may name a starter. Only if it passes, the injury features'
leakage checks run. Writes reports/v2_injury_checks.csv (counts only, no API data).
Exits 0 if both pass, 1 if a gate fails, 3 if there is not yet any data to check.
Run from the project root: python -m scripts.check_injuries [--seasons 2024 2023 2022]
"""

import argparse
import sys

import pandas as pd

from src.config import REPORTS_DIR
from src.injuries import gate_i, load_injuries, match_injuries
from src.injury_leaks import injury_check_report, real_code_flags
from src.lineups import link_fixtures, load_fixtures, load_lineups, match_lineups
from src.seasons import season_label
from src.splits import load_evaluation_matches

REPORT_PATH = REPORTS_DIR / "v2_injury_checks.csv"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2023, 2022])
    seasons = parser.parse_args(argv).seasons
    injuries, incomplete = load_injuries(seasons)
    covered = {season_label(season) for season in seasons if season not in incomplete}
    lineups, _ = load_lineups(load_fixtures(seasons)["fixture_id"])
    print(f"Injury records: {len(injuries)} in {', '.join(sorted(covered)) or 'no season yet'}; "
          f"types: {injuries['type'].value_counts().to_dict()}")
    result = gate_i(injuries, lineups)
    if not result["records_checked"]:
        print("Nothing to check yet: rerun after the injury lists and lineups are fetched.")
        return 3
    print(f"Gate I: {result['records_naming_a_starter']} of {result['records_checked']} 'Missing Fixture' records "
          f"on {result['fixtures_checked']} fixtures name a starter ({result['share']:.2%}); "
          f"{'pass' if result['passed'] else 'FAIL'} (limit 2%).")
    rows = [{"check": "Gate I: Missing Fixture records naming a starter", "random_cases": None,
             "random_flagged": None, "targeted_sample": "fixtures with lineups and injury records",
             "targeted_cases": result["records_checked"], "targeted_flagged": result["records_naming_a_starter"]}]
    status = 0 if result["passed"] else 1
    if result["passed"]:
        matches = load_evaluation_matches()
        linked = link_fixtures(load_fixtures(seasons), matches)
        report = injury_check_report(matches, match_lineups(lineups, linked), match_injuries(injuries, linked), covered)
        print("\n" + report.to_string(index=False))
        rows += report.to_dict("records")
        status = 0 if real_code_flags(report) == 0 else 1
    pd.DataFrame(rows).to_csv(REPORT_PATH, index=False)
    print(f"\nwritten {REPORT_PATH}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
