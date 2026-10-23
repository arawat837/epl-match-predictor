"""Hand-checked availability values on synthetic seasons."""

import math

import pandas as pd
import pytest

from src.availability import build_availability, count_missing_end_dates, unavailable_at_kickoff

START = pd.Timestamp("2016-08-13")


def fixtures(opponents: int, team: str = "A") -> pd.DataFrame:
    """`team` at home every week against a new opponent, all in 2016-17."""
    return pd.DataFrame({"date": [START + pd.Timedelta(weeks=week) for week in range(opponents)],
                         "season": "2016-17", "home": team,
                         "away": [f"Opp{week:02d}" for week in range(opponents)]})


def appearances(matches: pd.DataFrame, players: dict[int, dict[str, list]]) -> pd.DataFrame:
    """Rows for the home team: players[code][column] lists one value per match (defaults below)."""
    defaults = {"minutes": 90, "yellow_cards": 0, "red_cards": 0, "bps": 10, "ict_index": 5.0, "price": 5.0}
    rows = []
    for position, (_, match) in enumerate(matches.iterrows()):
        for player, values in players.items():
            row = {column: values.get(column, [default] * len(matches))[position] for column, default in defaults.items()}
            rows.append({"season": match["season"], "date": match["date"], "team": match["home"],
                         "home": match["home"], "away": match["away"], "player": player, **row})
    return pd.DataFrame(rows)


def values(rows: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    return build_availability(rows, matches)


def test_red_card_bans_only_the_next_league_match():
    matches = fixtures(3)
    table = values(appearances(matches, {1: {"red_cards": [1, 0, 0]}, 2: {}}), matches)
    assert table["home_banned_red"].tolist() == [[], [1], []]
    assert table["home_n_suspended"].tolist() == [0, 1, 0]


def test_fifth_yellow_by_match_19_bans_the_next_match():
    matches = fixtures(8)
    table = values(appearances(matches, {7: {"yellow_cards": [1, 1, 0, 1, 1, 1, 0, 0]}}), matches)
    assert [banned for banned in table["home_banned_yellow"]] == [[], [], [], [], [], [], [7], []]


def test_fifth_yellow_after_match_19_is_no_ban_but_tenth_by_32_is():
    matches = fixtures(23)
    late = [0] * 19 + [1, 1, 1, 1]  # yellows 1-4 in matches 20-23: no threshold reached
    early_ten = [1] * 10 + [0] * 13  # 5th at match 5, 10th at match 10
    table = values(appearances(matches, {3: {"yellow_cards": late}, 4: {"yellow_cards": early_ten}}), matches)
    bans = {position: banned for position, banned in enumerate(table["home_banned_yellow"]) if banned}
    assert bans == {5: [4], 10: [4]}


def test_second_yellow_red_bans_but_its_yellow_does_not_count():
    matches = fixtures(6)
    player = {"yellow_cards": [1, 1, 1, 1, 1, 0], "red_cards": [0, 0, 0, 0, 1, 0]}  # 5th yellow came with a red
    table = values(appearances(matches, {5: player}), matches)
    assert table.loc[5, "home_banned_red"] == [5]
    assert table.loc[5, "home_banned_yellow"] == []


def test_key_players_are_top_11_by_minutes_over_the_previous_10_matches():
    matches = fixtures(12)
    players = {code: {"minutes": [90 - code] * 12} for code in range(1, 13)}  # 12 regulars, code 12 plays least
    players[13] = {"minutes": [0] * 11 + [90]}  # plays only in the match being predicted
    table = values(appearances(matches, players), matches)
    assert table.loc[11, "home_key_players"] == list(range(1, 12))
    assert table.loc[11, "home_fpl_window"] == 10
    assert table.loc[0, "home_key_players"] == []


def test_squad_value_uses_prices_from_earlier_rows_only():
    matches = fixtures(3)
    players = {1: {"price": [5.0, 6.0, 7.0]}, 2: {"price": [4.0, 4.5, 9.9]}}
    table = values(appearances(matches, players), matches)
    assert table.loc[2, "home_squad_value"] == pytest.approx(6.0 + 4.5)  # not this match's 7.0 / 9.9
    assert table.loc[2, "home_squad_size"] == 2
    assert math.isnan(table.loc[0, "home_squad_value"])  # nobody has an earlier price
    assert table.loc[0, "home_squad_priced"] == 0


def test_form_is_minutes_weighted_over_the_previous_5_matches():
    matches = fixtures(7)
    players = {1: {"minutes": [90] * 7, "bps": [99, 10, 10, 10, 10, 10, 99]},
               2: {"minutes": [0, 30, 30, 30, 30, 30, 0], "bps": [0, 30, 30, 30, 30, 30, 0]}}
    table = values(appearances(matches, players), matches)
    assert table.loc[6, "home_form_bps"] == pytest.approx((90 * 10 + 30 * 30) / 120)  # matches 2-6 only


def test_unavailable_at_kickoff_counts_spells_started_before_the_match_date():
    day = pd.Timestamp("2020-01-10")
    spells = pd.DataFrame({
        "player": ["before", "on_the_day", "returned", "returns_on_day", "open"],
        "start": pd.to_datetime(["2020-01-01", "2020-01-10", "2019-12-01", "2020-01-01", "2019-11-01"]),
        "end": pd.to_datetime(["2020-02-01", "2020-02-01", "2020-01-05", "2020-01-10", None]),
    })
    assert unavailable_at_kickoff(spells, day) == {"before", "open"}
    assert count_missing_end_dates(spells) == 1
