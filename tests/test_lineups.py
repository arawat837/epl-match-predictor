"""Parsing API-Football fixtures and lineups, and linking them to matches.parquet (no network)."""

import json

import pandas as pd
import pytest

from src.api_football import cache_path
from src.lineups import (canonical_team, complete, fetch_order, fixture_table, fixtures_request, link_fixtures,
                         link_rate, lineup_request, lineup_rows, load_fixtures, load_lineups, match_lineups)


def fixture(fixture_id: int, date: str, home: tuple[int, str], away: tuple[int, str], round_number: int,
            season: int = 2024, status: str = "FT") -> dict:
    return {"fixture": {"id": fixture_id, "date": date, "status": {"short": status}},
            "league": {"season": season, "round": f"Regular Season - {round_number}"},
            "teams": {"home": {"id": home[0], "name": home[1]}, "away": {"id": away[0], "name": away[1]}}}


FIXTURES = {"response": [
    fixture(11, "2024-08-16T19:00:00+00:00", (33, "Manchester United"), (36, "Fulham"), 1),
    fixture(12, "2024-08-17T23:30:00+00:00", (39, "Wolves"), (49, "Chelsea"), 1),  # 00:30 BST on the 18th
    fixture(21, "2024-08-24T14:00:00+00:00", (36, "Fulham"), (62, "Sheffield Utd"), 2),
    fixture(22, "2024-08-24T14:00:00+00:00", (49, "Chelsea"), (33, "Manchester United"), 2, status="PST"),
]}


def side(team: tuple[int, str], first_id: int, starters: int = 11, keeper: bool = True) -> dict:
    players = [{"player": {"id": first_id + i, "name": f"P{first_id + i}", "pos": "G" if i == 0 and keeper else "M"}}
               for i in range(starters + 3)]
    return {"team": {"id": team[0], "name": team[1]}, "formation": "4-4-2",
            "startXI": players[:starters], "substitutes": players[starters:]}


LINEUP_11 = {"response": [side((33, "Manchester United"), 100), side((36, "Fulham"), 200)]}


def test_api_team_names_map_to_full_club_names():
    assert canonical_team("Manchester United") == "Manchester United"
    assert canonical_team("Wolves") == "Wolverhampton Wanderers"
    assert canonical_team("Sheffield Utd") == "Sheffield United"
    with pytest.raises(ValueError, match="API_TEAM_NAMES"):
        canonical_team("Real Madrid")


def test_fixture_table_has_uk_dates_rounds_and_full_names():
    table = fixture_table(FIXTURES)
    assert table["fixture_id"].tolist() == [11, 12, 21, 22]
    assert table["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-08-16", "2024-08-18", "2024-08-24", "2024-08-24"]
    assert table["round"].tolist() == [1, 1, 2, 2] and set(table["season"]) == {"2024-25"}
    assert table.loc[1, ["home", "away"]].tolist() == ["Wolverhampton Wanderers", "Chelsea"]


def test_lineup_rows_keep_starters_and_bench_and_complete_needs_two_full_xis():
    rows = lineup_rows(11, LINEUP_11)
    assert len(rows) == 28 and rows["starter"].sum() == 22
    assert rows.loc[rows["starter"] & (rows["position"] == "G"), "player_id"].tolist() == [100, 200]
    assert complete(rows)
    short = {"response": [side((33, "Manchester United"), 100, starters=10), side((36, "Fulham"), 200)]}
    assert not complete(lineup_rows(11, short))
    assert not complete(lineup_rows(11, {"response": [side((33, "Manchester United"), 100)]}))


def write_cache(directory, request, payload: dict) -> None:
    path = cache_path(*request, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cached_fixtures_drop_unfinished_matches_and_lineups_report_incomplete_ones(tmp_path):
    write_cache(tmp_path, fixtures_request(2024), FIXTURES)
    fixtures = load_fixtures([2024, 2023], tmp_path)  # 2023 is not cached: skipped
    assert fixtures["fixture_id"].tolist() == [11, 12, 21]
    write_cache(tmp_path, lineup_request(11), LINEUP_11)
    write_cache(tmp_path, lineup_request(12), {"response": [side((39, "Wolves"), 300, starters=9), side((49, "Chelsea"), 400)]})
    lineups, incomplete = load_lineups([11, 12, 21], tmp_path)  # 21 not cached
    assert set(lineups["fixture_id"]) == {11} and incomplete == [12]


def test_fetch_order_goes_season_by_season_then_round_by_round():
    early = fixture_table({"response": [fixture(5, "2022-08-06T14:00:00+00:00", (36, "Fulham"), (40, "Liverpool"), 1, 2022)]})
    fixtures = pd.concat([fixture_table(FIXTURES), early], ignore_index=True)
    assert fetch_order(fixtures, [2024, 2022]) == [11, 12, 21, 22, 5]
    assert fetch_order(fixtures, [2022]) == [5]


def test_linking_uses_uk_date_and_teams_and_assigns_sides(make_matches):
    matches = make_matches([("2024-08-16", "Manchester United", "Fulham", 1, 0),
                            ("2024-08-18", "Wolverhampton Wanderers", "Chelsea", 0, 2)])
    linked = link_fixtures(fixture_table(FIXTURES), matches)
    assert linked["match"].tolist()[:2] == [0, 1] and linked["match"].isna().sum() == 2
    assert link_rate(linked) == 0.5
    rows = match_lineups(lineup_rows(11, LINEUP_11), linked)
    assert set(rows.loc[rows["team"] == "Manchester United", "side"]) == {"home"}
    assert set(rows.loc[rows["team"] == "Fulham", "side"]) == {"away"} and set(rows["match"]) == {0}


def test_a_lineup_team_outside_its_fixture_raises(make_matches):
    matches = make_matches([("2024-08-16", "Manchester United", "Fulham", 1, 0)])
    linked = link_fixtures(fixture_table(FIXTURES), matches)
    wrong = lineup_rows(11, {"response": [side((33, "Manchester United"), 100), side((49, "Chelsea"), 400)]})
    with pytest.raises(ValueError, match="not in their fixture"):
        match_lineups(wrong, linked)
