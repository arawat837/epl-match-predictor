"""API-Football injury lists: requests and paging, parsing, linking, and Gate I (no network)."""

import json

import pandas as pd
import pytest

from src.api_football import cache_path
from src.injuries import (gate_i, injuries_request, injury_requests, injury_rows, load_injuries, match_injuries)
from src.lineups import fixture_table, link_fixtures


def record(fixture_id: int, team: tuple[int, str], player_id: int, kind: str = "Missing Fixture") -> dict:
    return {"player": {"id": player_id, "name": f"P{player_id}", "type": kind, "reason": "Knee Injury"},
            "team": {"id": team[0], "name": team[1]}, "fixture": {"id": fixture_id, "date": "2024-08-16T19:00:00+00:00"}}


UNITED, FULHAM = (33, "Manchester United"), (36, "Fulham")


def write_cache(directory, request, payload: dict) -> None:
    path = cache_path(*request, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_requests_add_further_pages_once_the_first_is_cached(tmp_path):
    assert injury_requests([2024], tmp_path) == [injuries_request(2024)]
    write_cache(tmp_path, injuries_request(2024), {"paging": {"current": 1, "total": 3}, "response": []})
    assert injury_requests([2024], tmp_path) == [injuries_request(2024), injuries_request(2024, 2),
                                                 injuries_request(2024, 3)]
    assert injuries_request(2024, 2)[1] == {"league": 39, "season": 2024, "page": 2}


def test_rows_keep_type_and_use_full_club_names():
    rows = injury_rows({"response": [record(11, UNITED, 7), record(11, (39, "Wolves"), 8, "Questionable")]})
    assert rows["team"].tolist() == ["Manchester United", "Wolverhampton Wanderers"]
    assert rows["type"].tolist() == ["Missing Fixture", "Questionable"]


def test_a_season_with_a_missing_page_is_left_out(tmp_path):
    write_cache(tmp_path, injuries_request(2024), {"paging": {"total": 2}, "response": [record(11, UNITED, 7)]})
    write_cache(tmp_path, injuries_request(2023), {"paging": {"total": 1}, "response": [record(5, FULHAM, 9)] * 2})
    injuries, incomplete = load_injuries([2024, 2023, 2022], tmp_path)
    assert incomplete == [2024, 2022] and injuries["fixture_id"].tolist() == [5]  # duplicates dropped
    write_cache(tmp_path, injuries_request(2024, 2), {"paging": {"total": 2}, "response": [record(12, UNITED, 8)]})
    assert set(load_injuries([2024], tmp_path)[0]["fixture_id"]) == {11, 12}


def lineup(fixture_id: int, starters: list[int], bench: list[int]) -> pd.DataFrame:
    return pd.DataFrame([{"fixture_id": fixture_id, "player_id": p, "starter": True} for p in starters]
                        + [{"fixture_id": fixture_id, "player_id": p, "starter": False} for p in bench])


def test_gate_i_counts_missing_records_that_name_a_starter():
    lineups = pd.concat([lineup(11, list(range(1, 12)), [20, 21]), lineup(12, list(range(31, 42)), [50])])
    injuries = injury_rows({"response": [record(11, UNITED, 20), record(11, UNITED, 5),  # 5 started: bad
                                         record(11, UNITED, 3, "Questionable"),  # doubtful: not counted
                                         record(12, FULHAM, 60), record(99, FULHAM, 1)]})  # 99 has no lineup
    result = gate_i(injuries, lineups)
    assert (result["fixtures_checked"], result["records_checked"], result["records_naming_a_starter"]) == (2, 3, 1)
    assert result["share"] == pytest.approx(1 / 3) and not result["passed"]
    clean = injuries[injuries["player_id"] != 5]
    assert gate_i(clean, lineups)["passed"] and gate_i(clean, lineups)["share"] == 0.0


def test_gate_i_fails_when_nothing_can_be_checked():
    assert not gate_i(injury_rows({"response": [record(99, FULHAM, 1)]}), lineup(11, list(range(1, 12)), []))["passed"]


def test_records_link_to_matches_with_sides_and_strangers_raise(make_matches):
    fixtures = fixture_table({"response": [{"fixture": {"id": 11, "date": "2024-08-16T19:00:00+00:00",
                                                        "status": {"short": "FT"}},
                                            "league": {"season": 2024, "round": "Regular Season - 1"},
                                            "teams": {"home": {"id": 33, "name": "Manchester United"},
                                                      "away": {"id": 36, "name": "Fulham"}}}]})
    linked = link_fixtures(fixtures, make_matches([("2024-08-16", "Manchester United", "Fulham", 1, 0)]))
    rows = match_injuries(injury_rows({"response": [record(11, UNITED, 7), record(11, FULHAM, 8)]}), linked)
    assert rows[["player_id", "side"]].values.tolist() == [[7, "home"], [8, "away"]]
    with pytest.raises(ValueError, match="not in their fixture"):
        match_injuries(injury_rows({"response": [record(11, (49, "Chelsea"), 9)]}), linked)
