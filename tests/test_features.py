import math

import pandas as pd
import pytest

from src.features import FeatureParams, build_features, feature_columns

# A: home win 2-0, away draw 1-1, home loss 0-1, then away at C.
FORM_ROWS = [
    ("2005-08-13", "A", "B", 2, 0),
    ("2005-08-20", "B", "A", 1, 1),
    ("2005-08-27", "A", "C", 0, 1),
    ("2005-09-03", "C", "A", 0, 3),
]
# X plays every season; Y is relegated after 2005-06 and returns in 2007-08; W is promoted in 2006-07.
SEASON_ROWS = [
    ("2005-08-13", "X", "Y", 1, 0),
    ("2005-08-20", "Y", "X", 1, 1),
    ("2006-08-19", "X", "W", 2, 0),
    ("2006-08-26", "W", "X", 0, 0),
    ("2007-08-18", "Y", "X", 0, 0),
]


@pytest.fixture
def form(make_matches) -> pd.DataFrame:
    return build_features(make_matches(FORM_ROWS))


@pytest.fixture
def seasons(make_matches) -> pd.DataFrame:
    return build_features(make_matches(SEASON_ROWS))


def test_feature_list(form):
    columns = feature_columns(form)
    assert len(columns) == 47
    assert columns[:3] == ["home_elo", "away_elo", "elo_diff"]
    assert {"home_ppg_last5_home_only", "away_gf_last10_away_only", "home_sot_against_last10",
            "away_days_rest", "home_season_ppg"} <= set(columns)
    assert not any(column.startswith("home_") and column.endswith("_away_only") for column in columns)


def test_first_match_has_no_form_or_rest(form):
    assert form.loc[0, ["home_ppg_last5", "home_gf_last5", "home_days_rest"]].isna().all()


def test_form_averages_previous_matches_only(form):
    a_at_c = form.loc[3]
    assert a_at_c["away_ppg_last5"] == pytest.approx(4 / 3)  # 3, 1, 0
    assert a_at_c["away_gf_last5"] == pytest.approx(1.0)  # 2, 1, 0
    assert a_at_c["away_ga_last5"] == pytest.approx(2 / 3)  # 0, 1, 1


def test_venue_form_uses_only_matches_at_that_venue(form):
    assert form.loc[3, "away_ppg_last5_away_only"] == 1.0  # only the draw at B
    assert form.loc[2, "home_ppg_last5_home_only"] == 3.0  # only the win over B
    assert form.loc[2, "home_ppg_last5"] == 2.0  # win and draw


def test_window_length_is_respected(make_matches):
    features = build_features(make_matches(FORM_ROWS), FeatureParams(windows=(2,)))
    assert features.loc[3, "away_ppg_last2"] == 0.5  # draw, loss


def test_shot_averages_for_and_against(form):
    a_at_c = form.loc[3]
    assert a_at_c["away_shots_for_last5"] == pytest.approx(11)  # 12, 11, 10
    assert a_at_c["away_shots_against_last5"] == pytest.approx(32 / 3)  # 10, 11, 11
    assert a_at_c["away_sot_for_last5"] == pytest.approx(3)  # 4, 3, 2
    assert a_at_c["away_sot_against_last5"] == pytest.approx(8 / 3)  # 2, 3, 3


def test_days_rest(form):
    assert form.loc[1, "away_days_rest"] == 7
    assert form.loc[3, "away_days_rest"] == 7


def test_season_ppg_in_the_first_season_has_no_prior(seasons):
    assert math.isnan(seasons.loc[0, "home_season_ppg"])
    assert seasons.loc[1, "home_season_ppg"] == 0.0  # Y lost its only match
    assert seasons.loc[1, "away_season_ppg"] == 3.0  # X won its only match


def test_season_ppg_carries_over_last_season_and_fades(seasons):
    assert seasons.loc[2, "home_season_ppg"] == pytest.approx(2.0)  # X: last season's 2.0, no games yet
    assert seasons.loc[3, "away_season_ppg"] == pytest.approx((3 + 5 * 2.0) / (1 + 5))


def test_promoted_and_returning_sides_get_the_promoted_prior(seasons):
    assert seasons.loc[2, "away_season_ppg"] == pytest.approx(1.0)  # W, promoted
    assert seasons.loc[3, "home_season_ppg"] == pytest.approx((0 + 5 * 1.0) / (1 + 5))
    assert seasons.loc[4, "home_season_ppg"] == pytest.approx(1.0)  # Y, back after a season away


def test_returning_side_starts_a_fresh_spell_but_continuing_side_keeps_its_history(seasons):
    y_back = seasons.loc[4]
    assert y_back[["home_ppg_last5", "home_days_rest"]].isna().all()
    assert y_back["away_ppg_last5"] == pytest.approx(2.0)  # X: 3, 1, 3, 1 across two seasons
    assert y_back["away_days_rest"] == 357
