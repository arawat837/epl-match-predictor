import numpy as np
import pandas as pd
import pytest

from src.config import FEATURES_PATH, HOLDOUT_SEASON, MATCHES_PATH
from src.dataset import join_features, load_model_table
from src.elo import EloParams, pre_match_elo
from src.features import build_features
from src.models import XGB_PARAMS, LogisticModel, XGBoostModel
from src.seasons import season_label
from src.tuning import (
    C_GRID,
    COMPACT_FEATURES,
    COMPACT_XGB_PARAMS,
    ELO_COLUMNS,
    elo_candidates,
    paired_difference,
    reporting_folds,
    tuning_folds,
    verdict,
    with_elo,
)

TUNING_SEASONS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20"]
REPORTING_SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
needs_data = pytest.mark.skipif(not (MATCHES_PATH.exists() and FEATURES_PATH.exists()),
                                reason="run the data and feature builds first")


def random_table(start_years: tuple[int, ...] = (2010, 2011, 2012), per_season: int = 60) -> pd.DataFrame:
    """Seasons of random results and random compact features."""
    rng = np.random.default_rng(0)
    frames = []
    for year in start_years:
        frame = pd.DataFrame({"date": pd.date_range(f"{year}-08-10", periods=per_season, freq="3D"),
                              "season": season_label(year), "result": rng.choice(["H", "D", "A"], per_season)})
        frames.append(frame.assign(**{column: rng.normal(size=per_season) for column in COMPACT_FEATURES}))
    return pd.concat(frames, ignore_index=True)


def test_grids_match_the_spec():
    assert len(elo_candidates()) == 5 * 4 * 3
    assert {(p.K, p.home_adv, p.carryover) for p in elo_candidates()} >= {(10, 50, 0.6), (30, 95, 0.9)}
    assert C_GRID == (0.01, 0.03, 0.1, 0.3, 1.0)
    assert len(COMPACT_FEATURES) == 7


def test_with_elo_recomputes_only_the_elo_columns(make_seasons):
    matches = make_seasons([2005, 2006])
    table = join_features(matches, build_features(matches))
    params = EloParams(K=30, home_adv=50, carryover=0.6)
    rebuilt = with_elo(table, matches, params)
    assert rebuilt.index.equals(table.index) and list(rebuilt.columns) == list(table.columns)
    np.testing.assert_allclose(rebuilt["elo_diff"], pre_match_elo(matches, params)["elo_diff"])
    assert not np.allclose(rebuilt["elo_diff"], table["elo_diff"])
    others = [column for column in table.columns if column not in ELO_COLUMNS]
    pd.testing.assert_frame_equal(rebuilt[others], table[others])


def test_logistic_model_uses_the_given_c():
    table = random_table()
    model = LogisticModel(COMPACT_FEATURES, C=0.03)
    model(table[table["season"] < "2012-13"], table[table["season"] == "2012-13"])
    assert model.fitted["2012-13"].named_steps["logisticregression"].C == 0.03


def test_compact_xgboost_uses_its_own_parameters_and_default_is_unchanged():
    table = random_table()
    model = XGBoostModel(COMPACT_FEATURES, params=COMPACT_XGB_PARAMS)
    model(table[table["season"] < "2012-13"], table[table["season"] == "2012-13"])
    fitted = model.fitted["2012-13"].get_params()
    assert (fitted["max_depth"], fitted["min_child_weight"], fitted["learning_rate"]) == (2, 20, 0.03)
    assert XGBoostModel(COMPACT_FEATURES).params == XGB_PARAMS


def test_paired_difference_and_verdict():
    reference = pd.Series([1.0, 1.0, 1.0, 1.0])
    difference, standard_error = paired_difference(pd.Series([0.9, 1.0, 0.8, 1.1]), reference)
    assert difference == pytest.approx(-0.05)
    assert standard_error == pytest.approx(np.std([-0.1, 0.0, -0.2, 0.1], ddof=1) / 2)
    assert verdict(0.01, 0.005) == "does not beat"
    assert verdict(-0.001, 0.005) == "beats, within noise"
    assert verdict(-0.02, 0.005) == "beats, clearly"


@needs_data
def test_tuning_and_reporting_windows_split_the_test_seasons():
    table = load_model_table()
    tuning, reporting = tuning_folds(table), reporting_folds(table)
    assert [fold.season for fold in tuning] == TUNING_SEASONS
    assert [fold.season for fold in reporting] == REPORTING_SEASONS
    for fold in tuning:
        assert set(fold.train["season"]).isdisjoint(REPORTING_SEASONS)
    for fold in reporting:
        assert set(TUNING_SEASONS) <= set(fold.train["season"])
        assert fold.train["date"].max() < fold.test["date"].min()
        assert all(season < HOLDOUT_SEASON for season in set(fold.train["season"]) | set(fold.test["season"]))
