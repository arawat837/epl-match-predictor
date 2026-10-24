"""EWMA form (plan amendment A1): exact values, spells, and leakage on synthetic and real matches."""

import pandas as pd
import pytest

import src.ewma_form as ewma_form
from src.config import MATCHES_PATH
from src.ewma_form import build_ewma_features, ewma_points_including_this_match
from src.leak_checks import earlier_plus_scrambled, features_differ, planted
from src.leak_samples import stratified_sample


def test_value_is_the_ewma_of_earlier_points_only(make_matches):
    # Arsenal: W, L, D at home, then the fourth match is scored from those three only
    matches = make_matches([("2020-08-15", "Arsenal", "Chelsea", 2, 0), ("2020-08-22", "Arsenal", "Everton", 0, 1),
                            ("2020-08-29", "Arsenal", "Fulham", 1, 1), ("2020-09-05", "Arsenal", "Burnley", 3, 0)])
    features = build_ewma_features(matches)
    weights = [1, 2 / 3, 4 / 9]  # span 5: alpha 1/3, most recent first
    expected = (1 * weights[0] + 0 * weights[1] + 3 * weights[2]) / sum(weights)
    assert features.loc[3, "home_points_ewma"] == pytest.approx(expected)
    assert features.loc[:2, "home_points_ewma"].isna().all()  # fewer than 3 earlier matches


def test_a_new_spell_restarts_the_ewma(seasons_with_promotion):
    features = build_ewma_features(seasons_with_promotion)
    seasons, home, away = seasons_with_promotion["season"], seasons_with_promotion["home"], seasons_with_promotion["away"]
    returning = seasons_with_promotion.index[(seasons == "2007-08") & ((home == "Team 19") | (away == "Team 19"))][:3]
    for match in returning:
        venue = "home" if home[match] == "Team 19" else "away"
        assert pd.isna(features.loc[match, f"{venue}_points_ewma"])


def test_diff_is_home_minus_away(seasons_with_promotion):
    features = build_ewma_features(seasons_with_promotion)
    pd.testing.assert_series_equal(features["points_ewma_diff"],
                                   features["home_points_ewma"] - features["away_points_ewma"], check_names=False)


def rebuilt_differs(matches: pd.DataFrame, full: pd.DataFrame, target: int) -> bool:
    return features_differ(build_ewma_features(earlier_plus_scrambled(matches, target)).loc[target], full.loc[target])


def test_planted_leak_is_flagged_and_the_real_code_is_not(seasons_with_promotion):
    targets = list(seasons_with_promotion.index[seasons_with_promotion["season"] == "2006-07"][100:105])
    real = build_ewma_features(seasons_with_promotion)
    assert not any(rebuilt_differs(seasons_with_promotion, real, target) for target in targets)
    with planted(ewma_form, "ewma_points", ewma_points_including_this_match):
        leaky = build_ewma_features(seasons_with_promotion)
        assert all(rebuilt_differs(seasons_with_promotion, leaky, target) for target in targets)


@pytest.mark.skipif(not MATCHES_PATH.exists(), reason="run `python -m scripts.build_dataset` first")
def test_real_matches_rebuild_identically_on_the_stratified_sample():
    from src.splits import load_evaluation_matches

    matches = load_evaluation_matches()
    full = build_ewma_features(matches)
    assert [target for target in stratified_sample(matches) if rebuilt_differs(matches, full, target)] == []
