"""Stage 7: availability and form data audit. No modelling; features.parquet untouched.

Fetches the FPL archive once (cached in data/raw/fpl/), links it to football-data matches,
prints coverage per season, the link rate and the ban check, and writes
data/processed/availability.parquet. The holdout is never downloaded or read.
Run from the project root: python -m scripts.audit_availability
"""

import pandas as pd

from src.audit import ban_outcomes, ban_summary, field_presence, fpl_coverage
from src.availability import build_availability
from src.config import PROCESSED_DIR
from src.fpl import download_fpl, load_fpl
from src.name_maps import check_link_rate, link_rows, load_overrides, minutes_weighted_link_rate, team_name_map
from src.splits import load_evaluation_matches

AVAILABILITY_PATH = PROCESSED_DIR / "availability.parquet"
PERCENT = "{:.1%}".format


def main() -> None:
    download_fpl()
    rows, matches = load_fpl(), load_evaluation_matches()
    names = team_name_map(list(rows["fpl_team"].unique()), load_overrides())
    linked = link_rows(rows, matches, dict(zip(names["fpl_name"], names["canonical"])))
    rate = minutes_weighted_link_rate(linked)
    check_link_rate(rate)

    print("Team-name map (non-exact matches):")
    print(names[names["method"] != "exact"].to_string(index=False))
    print(f"FPL team names: {len(names)}; minutes-weighted link rate (player code, club, match): {rate:.2%}\n")
    print("FPL coverage: matches where both sides have >= 11 players with minutes")
    print(fpl_coverage(linked, matches).to_string(float_format=PERCENT))
    print("\nShare of FPL rows with each field")
    print(field_presence(rows).to_string(float_format=PERCENT))

    fpl_matches = matches[matches["season"] >= rows["season"].min()]
    availability = build_availability(linked, fpl_matches)
    availability.to_parquet(AVAILABILITY_PATH)
    print(f"\nSaved {len(availability)} matches to {AVAILABILITY_PATH}")

    outcomes = ban_outcomes(availability, linked)
    outcomes.to_csv(PROCESSED_DIR / "ban_outcomes.csv", index=False)
    print("\nPredicted bans and what happened in the banned match")
    print(ban_summary(outcomes).to_string(float_format=PERCENT))


if __name__ == "__main__":
    main()
