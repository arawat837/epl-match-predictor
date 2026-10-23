import pytest

from src.rolling import team_appearances


def test_each_match_gives_one_appearance_per_side_from_its_point_of_view(make_matches):
    appearances = team_appearances(make_matches([("2005-08-13", "A", "B", 2, 1)])).set_index("team")
    assert appearances.loc["A", ["venue", "opponent", "goals_for", "goals_against", "points"]].tolist() == [
        "home", "B", 2, 1, 3]
    assert appearances.loc["B", ["venue", "opponent", "goals_for", "goals_against", "points"]].tolist() == [
        "away", "A", 1, 2, 0]
    assert appearances.loc["B", ["shots_for", "shots_against", "sot_for", "sot_against"]].tolist() == [
        11, 12, 3, 4]


def test_a_draw_is_one_point_each(make_matches):
    appearances = team_appearances(make_matches([("2005-08-13", "A", "B", 1, 1)]))
    assert appearances["points"].tolist() == [1, 1]


def test_spell_continues_over_consecutive_seasons_and_restarts_after_a_gap(make_matches):
    appearances = team_appearances(make_matches([
        ("2005-08-13", "A", "B", 1, 0),
        ("2006-08-12", "A", "B", 1, 0),
        ("2008-08-16", "A", "B", 1, 0),  # A and B both missed 2007-08
    ]))
    assert appearances[appearances["team"] == "A"]["spell"].tolist() == [0, 0, 1]


def test_two_matches_for_one_team_on_one_date_raise(make_matches):
    with pytest.raises(ValueError, match="two matches on one date"):
        team_appearances(make_matches([("2005-08-13", "A", "B", 1, 0), ("2005-08-13", "C", "A", 1, 0)]))
