"""Quality checks against the built data/processed/matches.parquet."""

import pandas as pd
import pytest

from src.config import FIRST_SEASON, MATCHES_PATH
from src.quality import (
    dates_outside_season,
    double_bookings,
    duplicate_fixtures,
    missing_values,
    rows_per_season,
)
from src.seasons import current_season, season_label

pytestmark = pytest.mark.skipif(
    not MATCHES_PATH.exists(), reason="run `python -m scripts.build_dataset` first"
)

IN_PROGRESS = season_label(current_season())


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return pd.read_parquet(MATCHES_PATH)


def test_covers_first_season_through_current(matches):
    seasons = sorted(matches["season"].unique())
    assert seasons[0] == season_label(FIRST_SEASON)
    assert seasons[-1] == IN_PROGRESS


def test_complete_seasons_have_380_rows_and_20_teams(matches):
    summary = rows_per_season(matches, IN_PROGRESS)
    assert summary["ok"].all(), summary[~summary["ok"]].to_string()


def test_no_missing_values(matches):
    assert missing_values(matches).empty


def test_no_duplicate_fixtures(matches):
    assert duplicate_fixtures(matches).empty


def test_no_team_plays_twice_on_one_date(matches):
    assert double_bookings(matches).empty


def test_every_date_falls_inside_its_season(matches):
    assert dates_outside_season(matches).empty


def test_result_matches_goals(matches):
    margin = matches["FTHG"] - matches["FTAG"]
    assert (matches.loc[margin > 0, "result"] == "H").all()
    assert (matches.loc[margin == 0, "result"] == "D").all()
    assert (matches.loc[margin < 0, "result"] == "A").all()
