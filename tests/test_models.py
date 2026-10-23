"""Walk-forward fold checks for the three models on the real feature table.

Every test season's fold is checked: chronology, burn-in and holdout exclusion, that the
logistic pipeline's imputer and scaler were fitted on the training window only, that
XGBoost early-stops on the last training season, that forecasts are valid
probabilities, and that a second run with the same seeds reproduces the first exactly.
"""

import numpy as np
import pandas as pd
import pytest

from src.config import FEATURES_PATH, FIRST_TEST_SEASON, HOLDOUT_SEASON, MATCHES_PATH
from src.data import MATCH_COLUMNS
from src.dataset import load_model_table, model_feature_columns
from src.evaluate import pre_match_view
from src.metrics import OUTCOMES
from src.models import LogisticModel, XGBoostModel, elo_only
from src.seasons import season_label, season_start
from src.splits import Fold, walk_forward_splits

pytestmark = pytest.mark.skipif(
    not (MATCHES_PATH.exists() and FEATURES_PATH.exists()),
    reason="run `python -m scripts.build_dataset` and `python -m scripts.build_features` first",
)

TEST_SEASONS = [season_label(year) for year in range(season_start(FIRST_TEST_SEASON), season_start(HOLDOUT_SEASON))]
MODELS = ["elo only", "logistic (all)", "xgboost"]


class Run:
    """Every model fitted and forecast on every fold, keeping the fitted models."""

    def __init__(self, folds: dict[str, Fold], columns: list[str]) -> None:
        self.logistic, self.xgboost = LogisticModel(columns), XGBoostModel(columns)
        models = {"elo only": elo_only, "logistic (all)": self.logistic, "xgboost": self.xgboost}
        self.forecasts = {(name, season): model(fold.train, pre_match_view(fold.test))
                          for season, fold in folds.items() for name, model in models.items()}


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    return load_model_table()


@pytest.fixture(scope="module")
def columns(table: pd.DataFrame) -> list[str]:
    return model_feature_columns(table)


@pytest.fixture(scope="module")
def folds(table: pd.DataFrame) -> dict[str, Fold]:
    return {fold.season: fold for fold in walk_forward_splits(table)}


@pytest.fixture(scope="module")
def first_run(folds: dict[str, Fold], columns: list[str]) -> Run:
    return Run(folds, columns)


@pytest.fixture(scope="module")
def second_run(folds: dict[str, Fold], columns: list[str]) -> Run:
    return Run(folds, columns)


def test_every_test_season_up_to_the_holdout_has_a_fold(folds):
    assert list(folds) == TEST_SEASONS


def test_model_inputs_exclude_goals_results_match_stats_and_odds(columns):
    assert len(columns) == 54
    assert set(columns).isdisjoint(MATCH_COLUMNS)


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_training_ends_before_testing_starts(folds, season):
    fold = folds[season]
    assert fold.train["date"].max() < fold.test["date"].min()


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_burn_in_rows_are_in_neither_train_nor_test(folds, season):
    fold = folds[season]
    assert not fold.train["burn_in"].any() and not fold.test["burn_in"].any()
    assert "2005-06" not in set(fold.train["season"]) | set(fold.test["season"])


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_holdout_season_never_appears(folds, season):
    fold = folds[season]
    assert all(seen < HOLDOUT_SEASON for seen in set(fold.train["season"]) | set(fold.test["season"]))


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_imputer_and_scaler_statistics_come_from_the_training_window_only(folds, columns, first_run, season):
    fold = folds[season]
    pipeline = first_run.logistic.fitted[season]
    imputer, scaler = pipeline.named_steps["simpleimputer"], pipeline.named_steps["standardscaler"]
    train = fold.train[columns]
    medians = train.median()
    imputed = train.fillna(medians)
    np.testing.assert_allclose(imputer.statistics_, medians.to_numpy())
    np.testing.assert_allclose(scaler.mean_, imputed.mean().to_numpy())
    np.testing.assert_allclose(scaler.scale_, imputed.std(ddof=0).to_numpy())
    with_test = pd.concat([train, fold.test[columns]])
    assert not np.allclose(scaler.mean_, with_test.fillna(with_test.median()).mean().to_numpy())


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_early_stopping_season_is_the_last_training_season(folds, first_run, season):
    last_training_season = folds[season].train["season"].max()
    assert first_run.xgboost.stopping_seasons[season] == last_training_season
    assert last_training_season == season_label(season_start(season) - 1)


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_forecasts_are_probabilities_that_sum_to_one(folds, first_run, season):
    for name in MODELS:
        forecast = first_run.forecasts[(name, season)]
        assert list(forecast.columns) == OUTCOMES
        assert forecast.index.equals(folds[season].test.index)
        values = forecast.to_numpy()
        assert ((values >= 0) & (values <= 1)).all(), name
        # XGBoost returns float32, so its rows sum to 1 only to float32 precision (~1e-7).
        np.testing.assert_allclose(values.sum(axis=1), 1.0, rtol=0, atol=1e-6, err_msg=name)


@pytest.mark.parametrize("season", TEST_SEASONS)
def test_fixed_seeds_reproduce_identical_results(first_run, second_run, season):
    for name in MODELS:
        pd.testing.assert_frame_equal(first_run.forecasts[(name, season)], second_run.forecasts[(name, season)],
                                      check_exact=True, obj=name)
    assert first_run.xgboost.trees[season] == second_run.xgboost.trees[season]
