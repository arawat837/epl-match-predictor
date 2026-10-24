import numpy as np
import pandas as pd
import pytest

from src.explain import contributions, home_minus_away_weights, logit_difference
from src.metrics import OUTCOMES
from src.models import LogisticModel

COLUMNS = ["a", "b", "c"]


@pytest.fixture
def fitted():
    rng = np.random.default_rng(0)
    train = pd.DataFrame(rng.normal(size=(600, 3)), columns=COLUMNS)
    train.loc[rng.choice(600, 60, replace=False), "b"] = np.nan  # the imputer has work to do
    train["result"] = rng.choice(OUTCOMES, size=600)
    model = LogisticModel(COLUMNS, C=0.03)
    return model.fit(train, "2016-17"), rng


def test_contributions_and_intercept_sum_to_the_logit_difference(fitted):
    pipeline, rng = fitted
    for _ in range(20):
        row = pd.DataFrame([rng.normal(size=3) * 2], columns=COLUMNS)
        table = contributions(pipeline, row, COLUMNS)
        _, intercept = home_minus_away_weights(pipeline)
        assert intercept + table["contribution"].sum() == pytest.approx(logit_difference(pipeline, row, COLUMNS), abs=1e-10)


def test_missing_feature_is_imputed_before_its_contribution(fitted):
    pipeline, _ = fitted
    row = pd.DataFrame([[0.5, np.nan, -1.0]], columns=COLUMNS)
    table = contributions(pipeline, row, COLUMNS).set_index("feature")
    _, intercept = home_minus_away_weights(pipeline)
    assert np.isfinite(table.loc["b", "contribution"])
    assert intercept + table["contribution"].sum() == pytest.approx(logit_difference(pipeline, row, COLUMNS), abs=1e-10)
