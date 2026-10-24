"""Temperature scaling: p_cal is proportional to p ** (1 / T), one parameter per test season.

For test season S, T is fitted by minimising log loss on the out-of-sample walk-forward
predictions for season S-1 (each made by a model that never saw S-1) and then applied to S.
Nothing from S or later seasons is used to fit S's temperature.
"""

import pandas as pd
from scipy.optimize import minimize_scalar

from src.metrics import OUTCOMES, log_loss
from src.seasons import season_label, season_start

TEMPERATURE_BOUNDS = (0.25, 4.0)


def temperature_scale(probabilities: pd.DataFrame, temperature: float) -> pd.DataFrame:
    """p ** (1 / T), renormalised per match; T = 1 leaves the forecast unchanged."""
    scaled = probabilities[OUTCOMES].to_numpy(dtype=float) ** (1 / temperature)
    return pd.DataFrame(scaled / scaled.sum(axis=1, keepdims=True), index=probabilities.index, columns=OUTCOMES)


def fit_temperature(probabilities: pd.DataFrame, outcomes: pd.Series) -> float:
    """The T in TEMPERATURE_BOUNDS minimising log loss of the scaled forecasts."""
    result = minimize_scalar(lambda temperature: log_loss(temperature_scale(probabilities, temperature), outcomes),
                             bounds=TEMPERATURE_BOUNDS, method="bounded")
    return float(result.x)


def previous_season(season: str) -> str:
    return season_label(season_start(season) - 1)


def calibrate_walk_forward(predictions: pd.DataFrame, first_season: str) -> tuple[pd.DataFrame, pd.Series]:
    """Scaled forecasts for every season from `first_season` on, each with T fitted on the season
    before; returns (forecasts with season and result, T per season)."""
    scaled, temperatures = [], {}
    for season in sorted(set(predictions["season"])):
        if season < first_season:
            continue
        fit_on = predictions[predictions["season"] == previous_season(season)]
        temperatures[season] = fit_temperature(fit_on[OUTCOMES], fit_on["result"])
        target = predictions[predictions["season"] == season]
        scaled.append(temperature_scale(target, temperatures[season]).join(target[["season", "result"]]))
    return pd.concat(scaled), pd.Series(temperatures, name="temperature")
