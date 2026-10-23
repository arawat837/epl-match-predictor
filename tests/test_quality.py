import pandas as pd

from src.quality import (
    dates_outside_season,
    double_bookings,
    duplicate_fixtures,
    failed_checks,
    missing_values,
    quality_report,
    rows_per_season,
)

IN_PROGRESS = "2006-07"


def season_summary(matches: pd.DataFrame, in_progress: str | None = IN_PROGRESS) -> pd.DataFrame:
    return rows_per_season(matches, in_progress).set_index("season")


def test_clean_table_passes_every_check(two_seasons):
    assert failed_checks(two_seasons, IN_PROGRESS) == []
    assert quality_report(two_seasons, IN_PROGRESS).endswith("All checks passed.")


def test_complete_season_counts_380_rows_and_20_teams(two_seasons):
    summary = season_summary(two_seasons)
    assert summary.loc["2005-06", ["rows", "teams"]].tolist() == [380, 20]
    assert summary.loc["2005-06", "ok"]


def test_complete_season_missing_a_match_is_flagged(two_seasons):
    short = two_seasons.drop(index=0)
    assert not season_summary(short).loc["2005-06", "ok"]
    assert "rows per season" in failed_checks(short, IN_PROGRESS)
    assert "FAILED: rows per season" in quality_report(short, IN_PROGRESS)


def test_in_progress_season_is_not_expected_complete(two_seasons):
    summary = season_summary(two_seasons)
    assert summary.loc["2006-07", "rows"] == 70
    assert summary.loc["2006-07", "ok"]


def test_partial_season_fails_once_it_should_be_complete(two_seasons):
    assert not season_summary(two_seasons, in_progress=None).loc["2006-07", "ok"]


def test_unstandardised_team_name_is_flagged(two_seasons):
    variant = two_seasons.copy()
    variant.loc[0, "home"] = "Team 00 FC"  # 21 distinct names in one season
    assert season_summary(variant).loc["2005-06", "teams"] == 21
    assert "rows per season" in failed_checks(variant, IN_PROGRESS)


def test_missing_values_are_counted_per_season_and_column(two_seasons):
    gappy = two_seasons.copy()
    gappy.loc[[0, 1], "HST"] = pd.NA
    missing = missing_values(gappy)
    assert list(missing.columns) == ["HST"]
    assert missing.loc["2005-06", "HST"] == 2
    assert "missing values" in failed_checks(gappy, IN_PROGRESS)


def test_no_missing_values_gives_empty_table(two_seasons):
    assert missing_values(two_seasons).empty


def test_repeated_fixture_is_flagged(two_seasons):
    repeated = pd.concat([two_seasons, two_seasons.iloc[[0]]], ignore_index=True)
    assert len(duplicate_fixtures(repeated)) == 2
    assert "duplicate fixtures" in failed_checks(repeated, IN_PROGRESS)


def test_same_fixture_in_another_season_is_not_a_duplicate(two_seasons):
    assert duplicate_fixtures(two_seasons).empty


def test_team_playing_twice_on_one_date_is_flagged(two_seasons):
    clash = two_seasons.copy()
    clash.loc[10, "date"] = clash.loc[0, "date"]  # move a round-2 match into round 1
    clashes = double_bookings(clash)
    assert set(clashes["team"]) == {clash.loc[10, "home"], clash.loc[10, "away"]}
    assert "double bookings" in failed_checks(clash, IN_PROGRESS)


def test_date_outside_its_season_is_flagged(two_seasons):
    wrong_year = two_seasons.copy()
    wrong_year.loc[0, "date"] = pd.Timestamp("2004-08-10")
    assert dates_outside_season(wrong_year).index.tolist() == [0]
    assert "dates outside season" in failed_checks(wrong_year, IN_PROGRESS)
