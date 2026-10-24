"""Gate 0, coverage half (docs/v2_lineup_plan.md): which Premier League seasons API-Football covers
for lineups, events, player statistics and injuries.

One request, cached under data/raw/api_football/ (pass --refresh to ask again). Needs the
API_FOOTBALL_KEY environment variable. Exits 1 if any season from 2015-16 to 2026-27 lacks lineups,
2 if the key is missing or the request is refused.
Run from the project root: python -m scripts.check_api_coverage
"""

import sys

from src.api_football import (FIRST_LINEUP_SEASON, LAST_LINEUP_SEASON, PREMIER_LEAGUE, ApiFootballError,
                              fetch, season_coverage, seasons_without_lineups)
from src.seasons import season_label


def main(refresh: bool = False) -> int:
    try:
        coverage = season_coverage(fetch("leagues", {"id": PREMIER_LEAGUE}, refresh=refresh))
    except ApiFootballError as error:
        print(error)
        return 2
    print(coverage.drop(columns="year").to_string(index=False))
    window = f"{season_label(FIRST_LINEUP_SEASON)} to {season_label(LAST_LINEUP_SEASON)}"
    missing = seasons_without_lineups(coverage)
    if missing:
        print(f"\nGate 0 coverage: FAIL. No lineup coverage for {', '.join(missing)} (needed: {window}).")
        return 1
    print(f"\nGate 0 coverage: pass. Lineups covered for every season {window}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(refresh="--refresh" in sys.argv[1:]))
