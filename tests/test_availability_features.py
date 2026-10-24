"""Hand-checked Stage 8 feature values on synthetic seasons."""

import math

import pandas as pd
import pytest

from src.availability_features import build_availability_features, group_columns
from tests.test_availability import appearances, fixtures

START = pd.Timestamp("2016-08-13")


def duel(weeks: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A and B meet weekly, alternating venues; A's 11 players cost 6.0, B's 11 cost 3.0."""
    matches = pd.DataFrame({"date": [START + pd.Timedelta(weeks=week) for week in range(weeks)],
                            "season": "2016-17",
                            "home": ["A" if week % 2 == 0 else "B" for week in range(weeks)],
                            "away": ["B" if week % 2 == 0 else "A" for week in range(weeks)]})
    rows = []
    for _, match in matches.iterrows():
        for team, price, first in (("A", 6.0, 1), ("B", 3.0, 101)):
            for player in range(first, first + 11):
                rows.append({"season": "2016-17", "date": match["date"], "team": team, "home": match["home"],
                             "away": match["away"], "player": player, "minutes": 90, "yellow_cards": 0,
                             "red_cards": 0, "bps": 10, "ict_index": 5.0, "price": price})
    return pd.DataFrame(rows), matches


def test_group_columns_are_home_away_and_diff():
    assert group_columns(["suspension", "form"]) == [
        "home_suspension", "away_suspension", "suspension_diff",
        "home_form_bps", "away_form_bps", "form_bps_diff", "home_form_ict", "away_form_ict", "form_ict_diff"]


def test_suspension_is_the_banned_players_share_of_last_10_match_minutes():
    matches = fixtures(3)
    players = {1: {"red_cards": [0, 1, 0], "minutes": [90, 45, 90]}, 2: {"minutes": [90, 90, 90]}}
    features = build_availability_features(appearances(matches, players), matches)
    assert features.loc[2, "home_suspension"] == pytest.approx((90 + 45) / (90 + 45 + 90 + 90))
    assert features.loc[1, "home_suspension"] == 0


def test_squad_value_is_key_player_value_over_the_league_mean_of_teams_seen_so_far():
    rows, matches = duel(3)
    features = build_availability_features(rows, matches)
    assert features.loc[2, "home_squad_value"] == pytest.approx(66 / 49.5)  # A: 11 x 6.0; mean of 66 and 33
    assert features.loc[2, "away_squad_value"] == pytest.approx(33 / 49.5)
    assert features.loc[2, "squad_value_diff"] == pytest.approx((66 - 33) / 49.5)
    assert math.isnan(features.loc[0, "home_squad_value"])  # nobody has played this season yet


def test_recent_absence_is_nan_for_the_first_5_matches_of_a_season():
    matches = fixtures(8)
    features = build_availability_features(appearances(matches, {p: {} for p in range(1, 12)}), matches)
    assert features.loc[:4, "home_recent_absence"].isna().all()
    assert features.loc[5:, "home_recent_absence"].eq(0).all()  # nobody missed the previous match


def test_recent_absence_is_the_key_minutes_share_of_players_out_of_the_previous_match():
    matches = fixtures(12)
    players = {code: {"minutes": [90] * 12} for code in range(1, 12)}
    players[3] = {"minutes": [90] * 10 + [0, 90]}  # out of match t-1 for t = match 12
    players[12] = {"minutes": [10] * 12}  # never a key player
    features = build_availability_features(appearances(matches, players), matches)
    assert features.loc[11, "home_recent_absence"] == pytest.approx(1 / 11)  # equal minutes over t-11..t-2
