"""Fetch Premier League fixture lists and announced lineups from API-Football into the raw cache
(data/raw/api_football/, gitignored), for the v2 lineup plan.

Season by season in the order given (default 2024-25, 2023-24, 2022-23: the seasons the free plan
allows), round by round within a season. At most --budget live requests per run (default 90, under
the free plan's 100 a day). Cached responses are never requested again, so rerunning continues where
the last run stopped. Needs API_FOOTBALL_KEY; exits 2 if a request is refused.
Run from the project root: python -m scripts.fetch_lineups [--budget 90] [--seasons 2024 2023 2022]
"""

import argparse
import sys

from src.api_football import ApiFootballError, fetch_missing
from src.lineups import fetch_order, fixtures_request, lineup_request, load_fixtures

DEFAULT_SEASONS = [2024, 2023, 2022]
DEFAULT_BUDGET = 90


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="live requests allowed this run")
    parser.add_argument("--seasons", type=int, nargs="+", default=DEFAULT_SEASONS, help="season start years, in order")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = arguments(argv)
    try:
        listed, _ = fetch_missing([fixtures_request(season) for season in args.seasons], args.budget)
        order = fetch_order(load_fixtures(args.seasons), args.seasons)
        fetched, missing = fetch_missing([lineup_request(fixture_id) for fixture_id in order], args.budget - listed)
    except ApiFootballError as error:
        print(error)
        print("Everything fetched before the refusal is cached; rerun later to continue.")
        return 2
    print(f"Fixture lists fetched: {listed}. Lineups fetched: {fetched}; still missing: {missing} of {len(order)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
