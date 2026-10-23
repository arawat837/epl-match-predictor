"""Hand-checked values for the feature spec in src/features.py."""

import math

import pandas as pd
import pytest

from src.features import build_features, feature_columns

# A and B play each other, alternating venues. Shots are 10 + goals, on target 2 + goals.
DUEL_ROWS = [
    ("2005-08-13", "A", "B", 2, 0),
    ("2005-08-20", "B", "A", 1, 1),
    ("2005-08-27", "A", "B", 0, 1),
    ("2005-09-03", "B", "A", 0, 3),
    ("2005-09-10", "A", "B", 1, 0),
    ("2005-09-30", "B", "A", 2, 2),  # 20 days after the last match
    ("2005-10-07", "A", "B", 0, 0),
]
# X plays both seasons, Y only the first, W is promoted for the second.
SEASON_ROWS = [
    ("2005-08-13", "X", "Y", 1, 0),
    ("2005-08-20", "Y", "X", 1, 1),
    ("2006-08-19", "X", "W", 2, 0),
    ("2006-08-26", "W", "X", 0, 0),
]


@pytest.fixture
def duel(make_matches) -> pd.DataFrame:
    return build_features(make_matches(DUEL_ROWS))


@pytest.fixture
def seasons(make_matches) -> pd.DataFrame:
    return build_features(make_matches(SEASON_ROWS))


def test_feature_list(duel):
    columns = feature_columns(duel)
    assert len(columns) == 54
    assert columns[:3] == ["elo_home", "elo_away", "elo_diff"]
    assert {"home_points_last5", "away_sot_for_last10", "home_points_venue_last5",
            "away_ga_venue_last5", "home_days_rest", "away_season_ppg",
            "points_last5_diff", "season_ppg_diff"} <= set(columns)


def test_rolling_needs_three_earlier_matches(duel):
    assert math.isnan(duel.loc[2, "home_points_last5"])  # A has played 2
    assert duel.loc[3, "away_points_last5"] == pytest.approx(4 / 3)  # A: 3, 1, 0


def test_all_venue_means_use_only_earlier_matches(duel):
    a_at_b = duel.loc[3]  # A's earlier matches: 2-0 home, 1-1 away, 0-1 home
    assert a_at_b["away_gf_last5"] == pytest.approx(1)
    assert a_at_b["away_ga_last5"] == pytest.approx(2 / 3)
    assert a_at_b["away_shots_for_last5"] == pytest.approx(11)  # 12, 11, 10
    assert a_at_b["away_shots_against_last5"] == pytest.approx(32 / 3)  # 10, 11, 11
    assert a_at_b["away_sot_for_last5"] == pytest.approx(3)  # 4, 3, 2


def test_last5_and_last10_windows(duel):
    assert duel.loc[6, "home_points_last5"] == pytest.approx(8 / 5)  # A: 1, 0, 3, 3, 1
    assert duel.loc[6, "home_points_last10"] == pytest.approx(11 / 6)  # A: 3, 1, 0, 3, 3, 1


def test_venue_form_uses_home_matches_for_home_team_and_away_matches_for_away_team(duel):
    final = duel.loc[6]
    assert final["home_points_venue_last5"] == pytest.approx(2)  # A at home: 3, 0, 3
    assert final["home_gf_venue_last5"] == pytest.approx(1)  # 2, 0, 1
    assert final["home_ga_venue_last5"] == pytest.approx(1 / 3)  # 0, 1, 0
    assert final["away_points_venue_last5"] == pytest.approx(1)  # B away: 0, 3, 0


def test_diff_is_home_minus_away(duel):
    final = duel.loc[6]
    assert final["points_last5_diff"] == pytest.approx(8 / 5 - 1)  # B: 1, 3, 0, 0, 1
    assert final["points_venue_last5_diff"] == pytest.approx(2 - 1)


def test_days_rest_is_capped_at_14_and_missing_before_a_first_match(duel):
    assert math.isnan(duel.loc[0, "home_days_rest"])
    assert duel.loc[1, "away_days_rest"] == 7
    assert duel.loc[5, "away_days_rest"] == 14  # 20 days, capped


def test_season_ppg_blends_in_five_games_of_last_seasons_ppg(seasons):
    assert seasons.loc[0, "home_season_ppg"] == pytest.approx(1.0)  # first season: 1.0
    assert seasons.loc[1, "away_season_ppg"] == pytest.approx((5 * 1.0 + 3) / (5 + 1))
    assert seasons.loc[2, "home_season_ppg"] == pytest.approx(2.0)  # X last season: 3, 1
    assert seasons.loc[3, "away_season_ppg"] == pytest.approx((5 * 2.0 + 3) / (5 + 1))


def test_promoted_team_uses_1_point_per_game(seasons):
    assert seasons.loc[2, "away_season_ppg"] == pytest.approx(1.0)
    assert seasons.loc[3, "home_season_ppg"] == pytest.approx((5 * 1.0 + 0) / (5 + 1))


def test_first_season_is_flagged_burn_in_and_kept(seasons):
    assert seasons["burn_in"].tolist() == [True, True, False, False]
