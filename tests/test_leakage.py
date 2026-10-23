"""Leakage tests on the real feature table: a match's features depend only on earlier matches.

For 50 random matches, the features are rebuilt from a table holding only matches dated
strictly before that match, plus the match itself with its goals, result and shots
replaced by values no real match has. If a feature read anything from the same day or
later, or from the match's own stats, the rebuilt value would differ from the stored one.
"""

import random

import pandas as pd
import pytest

from src.config import FEATURES_PATH, MATCHES_PATH
from src.data import ODDS_COLUMNS, POST_MATCH_COLUMNS
from src.features import build_features, feature_columns
from src.splits import load_evaluation_matches

pytestmark = pytest.mark.skipif(
    not (MATCHES_PATH.exists() and FEATURES_PATH.exists()),
    reason="run `python -m scripts.build_dataset` and `python -m scripts.build_features` first",
)

SAMPLE_SIZE = 50
SEED = 2026
MATCH_KEY = ["date", "home", "away"]
SCRAMBLED = {"FTHG": 0, "FTAG": 9, "result": "A", "HS": 99, "AS": 99, "HST": 99, "AST": 99}


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return load_evaluation_matches()


@pytest.fixture(scope="module")
def stored() -> pd.DataFrame:
    return pd.read_parquet(FEATURES_PATH)


@pytest.fixture(scope="module")
def sample(matches: pd.DataFrame) -> list[int]:
    return random.Random(SEED).sample(list(matches.index), SAMPLE_SIZE)


def earlier_plus_scrambled(matches: pd.DataFrame, target: int) -> pd.DataFrame:
    """Every match dated strictly before `target`, then `target` with its own stats scrambled."""
    match = matches.loc[[target]].copy()
    for column, value in SCRAMBLED.items():
        match.loc[target, column] = value
    earlier = matches[matches["date"] < match.loc[target, "date"]]
    return pd.concat([earlier, match])


@pytest.mark.parametrize("draw", range(SAMPLE_SIZE))
def test_features_use_only_earlier_matches_and_not_the_matchs_own_stats(draw, matches, stored, sample):
    target = sample[draw]
    rebuilt = build_features(earlier_plus_scrambled(matches, target)).loc[target]
    columns = feature_columns(stored)
    expected = stored.set_index(MATCH_KEY).loc[tuple(rebuilt[MATCH_KEY]), columns]
    pd.testing.assert_series_equal(
        rebuilt[columns].astype(float), expected.astype(float), check_names=False, rtol=1e-9)


def test_no_feature_is_a_same_match_stat_or_odds(stored):
    assert set(feature_columns(stored)).isdisjoint([*POST_MATCH_COLUMNS, *ODDS_COLUMNS])


def test_stored_features_cover_every_evaluation_match(matches, stored):
    assert len(stored) == len(matches)
    assert stored.set_index(MATCH_KEY).index.equals(matches.set_index(MATCH_KEY).index)
