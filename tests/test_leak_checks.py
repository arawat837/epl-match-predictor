"""The leakage check machinery on synthetic seasons: planted leaks must be flagged on the cases
where they show, and the real code must not be."""

import pandas as pd
import pytest

import src.features as features
from src.features import build_features
from src.leak_checks import (earlier_plus_scrambled, features_differ, flagged_features, planted,
                             season_ppg_including_this_match, scrambled_stats)
from src.leak_report import STAGE4_LEAKS
from src.leak_samples import targeted_sample
from src.metrics import OUTCOMES

STAT_COLUMNS = ["FTHG", "FTAG", "result", "HS", "AS", "HST", "AST"]


def outcome(home_goals: int, away_goals: int) -> str:
    return "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D"


@pytest.mark.parametrize("home_goals, away_goals", [(0, 0), (2, 2), (1, 0), (5, 0), (0, 1), (0, 9), (3, 4)])
def test_scrambled_stats_differ_from_the_real_ones_in_every_column(home_goals, away_goals):
    real = {"FTHG": home_goals, "FTAG": away_goals, "result": outcome(home_goals, away_goals),
            "HS": 14, "AS": 9, "HST": 6, "AST": 3}
    scrambled = scrambled_stats(home_goals, away_goals)
    assert scrambled["result"] in OUTCOMES and scrambled["result"] == outcome(scrambled["FTHG"], scrambled["FTAG"])
    assert all(scrambled[column] != real[column] for column in STAT_COLUMNS)


def test_planted_replaces_a_function_only_inside_the_block():
    original = features.days_rest
    with planted(features, "days_rest", lambda long: None):
        assert features.days_rest is not original
    assert features.days_rest is original


def test_planted_restores_the_function_after_an_error():
    original = features.days_rest
    with pytest.raises(RuntimeError), planted(features, "days_rest", lambda long: None):
        raise RuntimeError
    assert features.days_rest is original


def test_rebuild_table_holds_earlier_matches_then_the_scrambled_match(seasons_with_promotion):
    target = seasons_with_promotion.index[seasons_with_promotion["season"] == "2006-07"][15]
    table = earlier_plus_scrambled(seasons_with_promotion, target)
    assert table.index[-1] == target
    assert (table["date"].iloc[:-1] < table.loc[target, "date"]).all()
    real = seasons_with_promotion.loc[target]
    assert table.loc[target, STAT_COLUMNS].tolist() == list(scrambled_stats(real["FTHG"], real["FTAG"]).values())


@pytest.mark.parametrize("home_goals, away_goals", [(0, 2), (0, 0), (2, 1)], ids=["away win", "0-0 draw", "home win"])
def test_season_ppg_leak_is_flagged_whatever_the_real_result(make_matches, home_goals, away_goals):
    matches = make_matches([("2020-08-15", "Arsenal", "Burnley", home_goals, away_goals),
                            ("2020-08-15", "Chelsea", "Everton", 1, 0),
                            ("2020-08-22", "Burnley", "Chelsea", 1, 1),
                            ("2020-08-22", "Everton", "Arsenal", 0, 3)])
    with planted(features, "season_ppg", season_ppg_including_this_match):
        assert flagged_features(matches, build_features(matches), [0]) == 1


def test_matching_missing_values_are_not_a_difference():
    assert not features_differ(pd.Series([1.0, float("nan")]), pd.Series([1.0 + 1e-12, float("nan")]))
    assert features_differ(pd.Series([1.0, float("nan")]), pd.Series([1.0, 2.0]))


@pytest.mark.parametrize("check, name, leaky, target", STAGE4_LEAKS, ids=[leak[0] for leak in STAGE4_LEAKS])
def test_planted_leak_is_flagged_on_its_targeted_case_and_the_real_code_is_not(check, name, leaky, target,
                                                                                 seasons_with_promotion):
    targets = targeted_sample(seasons_with_promotion, target, size=2)
    assert flagged_features(seasons_with_promotion, build_features(seasons_with_promotion), targets) == 0
    with planted(features, name, leaky):
        assert flagged_features(seasons_with_promotion, build_features(seasons_with_promotion), targets) == len(targets)
