import pytest

from src.elo import EloParams, expected_home_score, goal_difference_multiplier, pre_match_elo

NO_HOME_EDGE = EloParams(k=20, home_advantage=0)


@pytest.mark.parametrize("difference, weight", [
    (0, 1.0), (1, 1.0), (-1, 1.0), (2, 1.5), (3, 1.75), (4, 1.875), (-5, 2.0),
])
def test_goal_difference_multiplier(difference, weight):
    assert goal_difference_multiplier(difference) == weight


def test_expected_home_score():
    assert expected_home_score(1500, 1500, home_advantage=0) == 0.5
    assert expected_home_score(1500, 1500, home_advantage=60) > 0.5
    assert expected_home_score(1900, 1500, home_advantage=0) == pytest.approx(10 / 11)


def test_teams_start_at_1500_and_a_win_moves_k_times_the_surprise(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", 1, 0), ("2005-08-20", "A", "B", 0, 0)])
    elo = pre_match_elo(matches, NO_HOME_EDGE)
    assert elo.loc[0, ["home_elo", "away_elo"]].tolist() == [1500, 1500]
    assert elo.loc[1, ["home_elo", "away_elo"]].tolist() == [1510, 1490]
    assert elo.loc[1, "elo_diff"] == 20


def test_a_bigger_margin_moves_ratings_further(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", 3, 0), ("2005-08-20", "A", "B", 0, 0)])
    assert pre_match_elo(matches, NO_HOME_EDGE).loc[1, "home_elo"] == 1500 + 20 * 1.75 * 0.5


def test_with_home_advantage_a_home_draw_between_equals_costs_rating(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", 0, 0), ("2005-08-20", "A", "B", 0, 0)])
    assert pre_match_elo(matches, EloParams(home_advantage=60)).loc[1, "home_elo"] < 1500


def test_ratings_only_reflect_earlier_dates(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", 5, 0), ("2005-08-13", "C", "D", 0, 5)])
    elo = pre_match_elo(matches, NO_HOME_EDGE)
    assert elo[["home_elo", "away_elo"]].eq(1500).all().all()


def test_unplayed_match_changes_nothing(make_matches):
    matches = make_matches([("2005-08-13", "A", "B", None, None), ("2005-08-20", "A", "B", 1, 0)])
    assert pre_match_elo(matches).loc[1, ["home_elo", "away_elo"]].tolist() == [1500, 1500]


def test_returning_team_resumes_its_rating_and_a_new_team_starts_at_1500(make_matches):
    matches = make_matches([
        ("2005-08-13", "A", "B", 1, 0),
        ("2006-08-12", "C", "D", 1, 0),  # A out of the league in 2006-07
        ("2007-08-11", "A", "E", 1, 0),
    ])
    assert pre_match_elo(matches, NO_HOME_EDGE).loc[2, ["home_elo", "away_elo"]].tolist() == [1510, 1500]
