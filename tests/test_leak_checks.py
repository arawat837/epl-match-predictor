"""The leakage check machinery on synthetic seasons: planted leaks must be flagged on the cases
where they show, and the real code must not be."""

import pandas as pd
import pytest

import src.features as features
from src.features import build_features
from src.leak_checks import SCRAMBLED, earlier_plus_scrambled, features_differ, flagged_features, planted
from src.leak_report import STAGE4_LEAKS
from src.leak_samples import targeted_sample


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
    assert table.loc[target, list(SCRAMBLED)].tolist() == list(SCRAMBLED.values())


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
