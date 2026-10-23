import pytest

from src.config import MATCHES_PATH
from src.elo import EloParams, expected_home, goal_difference_multiplier, pre_match_elo, update
from src.splits import load_evaluation_matches

PARAMS = EloParams(K=20, home_adv=80)


def test_expected_home_for_1600_v_1500_with_home_advantage_80():
    assert expected_home(1600, 1500, home_adv=80) == pytest.approx(0.738, abs=5e-4)


@pytest.mark.parametrize("home_goals, away_goals, new_home, new_away", [
    (1, 0, 1605.24, 1494.76),  # home win
    (0, 0, 1595.24, 1504.76),  # draw
    (0, 1, 1585.24, 1514.76),  # away win
])
def test_new_ratings_for_1600_v_1500(home_goals, away_goals, new_home, new_away):
    r_home, r_away = update(1600, 1500, home_goals, away_goals, PARAMS)
    assert r_home == pytest.approx(new_home, abs=0.005)
    assert r_away == pytest.approx(new_away, abs=0.005)
    assert r_home - 1600 == pytest.approx(-(r_away - 1500))


@pytest.mark.parametrize("difference, g", [
    (0, 1.0), (1, 1.0), (-1, 1.0), (2, 1.5), (-2, 1.5), (3, 1.75), (4, 1.875),
])
def test_goal_difference_multiplier(difference, g):
    assert goal_difference_multiplier(difference) == g


@pytest.mark.skipif(not MATCHES_PATH.exists(), reason="run `python -m scripts.build_dataset` first")
def test_first_match_in_the_dataset_is_rated_1500_v_1500_pre_match():
    matches = load_evaluation_matches()
    first = pre_match_elo(matches).loc[matches["date"].idxmin()]
    assert first[["elo_home", "elo_away", "elo_diff"]].tolist() == [1500, 1500, 0]


def test_stored_ratings_are_pre_match(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", 1, 0), ("2005-08-20", "A", "B", 0, 0)])
    elo = pre_match_elo(matches, PARAMS)
    assert elo.loc[0, ["elo_home", "elo_away"]].tolist() == [1500, 1500]
    assert tuple(elo.loc[1, ["elo_home", "elo_away"]]) == pytest.approx(update(1500, 1500, 1, 0, PARAMS))


def test_season_change_regresses_last_seasons_teams_and_starts_newcomers_at_1450(make_matches):
    matches = make_matches([
        ("2005-08-13", "X", "Y", 1, 0),
        ("2006-08-19", "X", "W", 0, 0),  # Y relegated, W promoted
        ("2007-08-18", "Y", "X", 0, 0),  # Y back after a season away
    ])
    elo = pre_match_elo(matches, PARAMS)
    x_after_first, _ = update(1500, 1500, 1, 0, PARAMS)
    assert elo.loc[1, "elo_home"] == pytest.approx(1500 + 0.75 * (x_after_first - 1500))
    assert elo.loc[1, "elo_away"] == 1450
    assert elo.loc[2, "elo_home"] == 1450
