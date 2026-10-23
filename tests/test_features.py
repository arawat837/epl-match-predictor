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
# X plays both seasons, Y only the first, W is promoted for the second. The first season's
# matches are in May so X's summer break (98 days) stays inside one spell.
SEASON_ROWS = [
    ("2006-05-06", "X", "Y", 1, 0),
    ("2006-05-13", "Y", "X", 1, 1),
    ("2006-08-19", "X", "W", 2, 0),
    ("2006-08-26", "W", "X", 0, 0),
]


# R plays 2005-06, misses 2006-07 (469 days out) and returns in 2007-08. S plays every
# season with normal breaks: 105-day summers and in-season gaps up to 140 days.
SPELL_ROWS = [
    ("2006-04-15", "R", "S", 1, 0),
    ("2006-04-22", "S", "R", 1, 1),
    ("2006-04-29", "R", "S", 2, 0),
    ("2006-05-06", "S", "R", 0, 1),
    ("2006-08-19", "S", "T", 2, 0),
    ("2007-01-06", "T", "S", 1, 1),
    ("2007-05-05", "S", "T", 1, 0),
    ("2007-08-18", "R", "S", 0, 0),  # R's return
    ("2007-08-25", "S", "R", 1, 0),
    ("2007-09-01", "R", "S", 2, 2),
    ("2007-09-15", "S", "R", 0, 0),
]


@pytest.fixture
def spell(make_matches) -> pd.DataFrame:
    return build_features(make_matches(SPELL_ROWS))


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


def test_team_back_after_a_missed_season_starts_a_new_spell(spell):
    r_returns = spell.loc[7]
    assert r_returns[["home_points_last5", "home_points_last10", "home_points_venue_last5",
                      "home_shots_for_last5", "home_days_rest"]].isna().all()
    assert r_returns["home_season_ppg"] == pytest.approx(1.0)  # last_season_ppg 1.0, no games yet


def test_new_spell_rolling_waits_for_three_matches_in_the_spell(spell):
    assert math.isnan(spell.loc[9, "home_points_last5"])  # R: 2 matches since returning
    assert spell.loc[10, "away_points_last5"] == pytest.approx(2 / 3)  # R: 1, 0, 1; not 3, 3 from before
    assert math.isnan(spell.loc[10, "away_points_venue_last5"])  # R: 1 away match since returning


def test_summer_breaks_and_long_in_season_gaps_keep_the_spell(spell):
    assert spell.loc[4, "home_points_last5"] == pytest.approx(0.25)  # S across summer: 0, 1, 0, 0
    assert spell.loc[4, "home_days_rest"] == 14
    s_away = spell.loc[7]
    assert s_away["away_points_last5"] == pytest.approx(7 / 5)  # S: 0, 0, 3, 1, 3
    assert s_away["away_days_rest"] == 14
    assert s_away["away_season_ppg"] == pytest.approx(7 / 3)  # S last season: 3, 1, 3


def test_spell_breaks_only_when_the_gap_exceeds_200_days(make_matches):
    start = pd.Timestamp("2005-08-13")
    dates = [start, start + pd.Timedelta(days=150), start + pd.Timedelta(days=350),
             start + pd.Timedelta(days=551)]  # gaps of 150, 200 and 201 days
    features = build_features(make_matches([(day.strftime("%Y-%m-%d"), "A", "B", 1, 0) for day in dates]))
    assert features.loc[[1, 2], "home_days_rest"].tolist() == [14, 14]
    assert math.isnan(features.loc[3, "home_days_rest"])
