import numpy as np
import pandas as pd
import pytest

import src.calibration as calibration
from src.calibration import calibrate_walk_forward, fit_temperature, temperature_scale
from src.metrics import OUTCOMES

RNG = np.random.default_rng(0)


def forecasts(n: int, seasons: list[str]) -> pd.DataFrame:
    raw = RNG.uniform(0.05, 1.0, size=(n * len(seasons), 3))
    frame = pd.DataFrame(raw / raw.sum(axis=1, keepdims=True), columns=OUTCOMES)
    return frame.assign(season=np.repeat(seasons, n), result=RNG.choice(OUTCOMES, size=len(frame)))


def test_temperature_one_leaves_probabilities_unchanged():
    frame = forecasts(200, ["2016-17"])
    np.testing.assert_allclose(temperature_scale(frame, 1.0).to_numpy(), frame[OUTCOMES].to_numpy(), rtol=0, atol=1e-12)


@pytest.mark.parametrize("temperature", [0.25, 0.7, 1.3, 4.0])
def test_scaled_probabilities_are_in_0_1_and_sum_to_1(temperature):
    scaled = temperature_scale(forecasts(300, ["2016-17"]), temperature).to_numpy()
    assert ((scaled >= 0) & (scaled <= 1)).all()
    np.testing.assert_allclose(scaled.sum(axis=1), 1.0, atol=1e-12)


def test_fitting_recovers_a_known_temperature():
    frame = forecasts(20000, ["2016-17"])
    truth = temperature_scale(frame, 2.0).to_numpy()
    draws = [RNG.choice(OUTCOMES, p=row) for row in truth]
    assert fit_temperature(frame[OUTCOMES], pd.Series(draws)) == pytest.approx(2.0, abs=0.15)


def test_each_seasons_temperature_is_fitted_on_the_season_before_only(monkeypatch):
    frame = forecasts(100, ["2015-16", "2016-17", "2017-18", "2018-19"])
    fitted_on: list[set[str]] = []
    original = calibration.fit_temperature

    def spy(probabilities: pd.DataFrame, outcomes: pd.Series) -> float:
        fitted_on.append(set(frame.loc[probabilities.index, "season"]))
        return original(probabilities, outcomes)

    monkeypatch.setattr(calibration, "fit_temperature", spy)
    scaled, temperatures = calibrate_walk_forward(frame, "2016-17")
    assert list(temperatures.index) == ["2016-17", "2017-18", "2018-19"]
    assert fitted_on == [{"2015-16"}, {"2016-17"}, {"2017-18"}]
    assert set(scaled["season"]) == {"2016-17", "2017-18", "2018-19"}
