import numpy as np
import pandas as pd
import pytest
from scipy.optimize import check_grad

from src.metrics import OUTCOMES, one_hot
from src.offset import (BASE_COLUMNS, OffsetModel, Standardiser, fit_offset, objective,
                        offset_probabilities)

RNG = np.random.default_rng(0)


def random_base(n: int) -> np.ndarray:
    raw = RNG.uniform(0.1, 1.0, size=(n, 3))
    return raw / raw.sum(axis=1, keepdims=True)


def test_zero_weights_reproduce_the_base_probabilities():
    base = random_base(500)
    features = RNG.normal(size=(500, 4))
    probabilities = offset_probabilities(np.log(base), features, np.zeros((4, 3)))
    np.testing.assert_allclose(probabilities, base, rtol=0, atol=1e-12)


def test_probabilities_are_in_0_1_and_sum_to_1_for_any_weights():
    probabilities = offset_probabilities(np.log(random_base(300)), RNG.normal(size=(300, 3)) * 5,
                                         RNG.normal(size=(3, 3)) * 3)
    assert ((probabilities >= 0) & (probabilities <= 1)).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, atol=1e-12)


def test_gradient_matches_finite_differences():
    base, features = random_base(200), RNG.normal(size=(200, 3))
    observed = one_hot(pd.Series(RNG.choice(OUTCOMES, size=200)))
    start = RNG.normal(scale=0.2, size=6)
    error = check_grad(lambda w: objective(w, np.log(base), features, observed, 0.01)[0],
                       lambda w: objective(w, np.log(base), features, observed, 0.01)[1], start)
    assert error < 1e-6


def test_fitted_draw_column_is_zero_and_fit_beats_base_in_sample():
    base = np.tile([0.45, 0.27, 0.28], (2000, 1))
    signal = RNG.normal(size=(2000, 1))
    home_win = RNG.uniform(size=2000) < 1 / (1 + np.exp(-(signal[:, 0] - 0.2)))
    results = pd.Series(np.where(home_win, "H", RNG.choice(["D", "A"], size=2000)))
    weights = fit_offset(np.log(base), signal, one_hot(results), lam=0.001)
    assert weights[0, 1] == 0 and weights[0, 0] > 0
    fitted = offset_probabilities(np.log(base), signal, weights)
    observed = one_hot(results)
    assert -np.log((fitted * observed).sum(axis=1)).mean() < -np.log((base * observed).sum(axis=1)).mean()


def test_standardiser_uses_training_statistics_and_zeroes_nans():
    train = pd.DataFrame({"x": [1.0, 3.0, np.nan], "constant": [2.0, 2.0, 2.0]})
    scaler = Standardiser.fit(train)
    test = pd.DataFrame({"x": [2.0, np.nan, 5.0], "constant": [2.0, 7.0, 2.0]})
    np.testing.assert_allclose(scaler.transform(test), [[0.0, 0.0], [0.0, 5.0], [3.0, 0.0]])


def test_offset_model_records_its_training_seasons():
    def frame(season: str, n: int) -> pd.DataFrame:
        base = pd.DataFrame(random_base(n), columns=BASE_COLUMNS)
        return base.assign(season=season, result=RNG.choice(OUTCOMES, size=n), x=RNG.normal(size=n))
    train = pd.concat([frame("2016-17", 100), frame("2017-18", 100)], ignore_index=True)
    test = frame("2018-19", 50)
    model = OffsetModel(["x"], lam=0.01)
    forecast = model(train, test)
    assert model.training_seasons["2018-19"] == ["2016-17", "2017-18"]
    assert list(forecast.columns) == OUTCOMES and forecast.index.equals(test.index)
