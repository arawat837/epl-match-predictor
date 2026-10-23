import math

import pandas as pd
import pytest

from src.metrics import OUTCOMES, accuracy, log_loss, ranked_probability_score

UNIFORM = [1 / 3, 1 / 3, 1 / 3]


def forecast(*rows: list[float]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=OUTCOMES)


def observed(*results: str) -> pd.Series:
    return pd.Series(list(results))


def test_log_loss_is_negative_log_of_the_observed_outcomes_probability():
    assert log_loss(forecast([0.5, 0.3, 0.2]), observed("D")) == pytest.approx(-math.log(0.3))
    assert log_loss(forecast(UNIFORM), observed("A")) == pytest.approx(math.log(3))


def test_log_loss_is_infinite_when_what_happened_had_zero_probability():
    assert log_loss(forecast([1.0, 0.0, 0.0]), observed("A")) == math.inf


def test_rps_hand_computed_values():
    assert ranked_probability_score(forecast(UNIFORM), observed("H")) == pytest.approx(5 / 18)
    assert ranked_probability_score(forecast(UNIFORM), observed("D")) == pytest.approx(1 / 9)
    assert ranked_probability_score(forecast([1.0, 0.0, 0.0]), observed("H")) == 0
    assert ranked_probability_score(forecast([0.0, 0.0, 1.0]), observed("H")) == pytest.approx(1)
    assert ranked_probability_score(forecast([0.9, 0.1, 0.0]), observed("H")) == pytest.approx(0.005)


def test_rps_penalises_distance_along_h_d_a_but_log_loss_does_not():
    draw_heavy, away_heavy = forecast([0.2, 0.5, 0.3]), forecast([0.2, 0.3, 0.5])
    assert ranked_probability_score(draw_heavy, observed("H")) == pytest.approx(0.365)
    assert ranked_probability_score(away_heavy, observed("H")) == pytest.approx(0.445)
    assert log_loss(draw_heavy, observed("H")) == log_loss(away_heavy, observed("H"))


def test_metrics_are_means_over_matches():
    probabilities, results = forecast([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]), observed("H", "H")
    assert ranked_probability_score(probabilities, results) == pytest.approx(0.5)
    assert accuracy(probabilities, results) == 0.5


def test_accuracy_picks_most_probable_outcome_and_breaks_ties_toward_home():
    assert accuracy(forecast([0.2, 0.5, 0.3], UNIFORM), observed("D", "H")) == 1.0


@pytest.mark.parametrize("probabilities, results", [
    (forecast([0.5, 0.3, 0.2])[["A", "D", "H"]], observed("H")),  # wrong column order
    (forecast([0.5, 0.5, 0.5]), observed("H")),  # doesn't sum to 1
    (forecast([1.2, -0.1, -0.1]), observed("H")),  # negative
    (forecast([0.5, 0.3, 0.2]), pd.Series(["H"], index=[7])),  # misaligned
    (forecast([0.5, 0.3, 0.2]), observed("X")),  # not an outcome
])
def test_invalid_forecasts_raise(probabilities, results):
    with pytest.raises(ValueError):
        log_loss(probabilities, results)
