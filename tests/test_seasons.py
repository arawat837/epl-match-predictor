from datetime import date

from src.seasons import current_season, season_code, season_label, season_start, seasons_through_current


def test_season_code():
    assert season_code(2005) == "0506"
    assert season_code(2025) == "2526"
    assert season_code(2099) == "9900"


def test_season_label_round_trips_to_start_year():
    assert season_label(2009) == "2009-10"
    assert season_start(season_label(2009)) == 2009


def test_current_season_rolls_over_in_august():
    assert current_season(date(2026, 7, 31)) == 2025
    assert current_season(date(2026, 8, 1)) == 2026
    assert current_season(date(2027, 5, 20)) == 2026


def test_seasons_through_current_includes_both_ends():
    seasons = seasons_through_current(2005, today=date(2026, 10, 24))
    assert seasons[0] == 2005
    assert seasons[-1] == 2026
    assert len(seasons) == 22
