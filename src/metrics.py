"""Scoring rules for H/D/A probability forecasts.

A forecast is a DataFrame with columns OUTCOMES and one row per match; the observed
outcomes are a Series of "H"/"D"/"A" on the same index.
"""

import numpy as np
import pandas as pd

OUTCOMES = ["H", "D", "A"]  # ordered: RPS treats a draw as between a home and an away win


def check_forecasts(probabilities: pd.DataFrame, outcomes: pd.Series) -> None:
    """Raise unless each row is a probability distribution over OUTCOMES, aligned with valid outcomes."""
    if list(probabilities.columns) != OUTCOMES:
        raise ValueError(f"forecast columns must be {OUTCOMES}, got {list(probabilities.columns)}")
    if not probabilities.index.equals(outcomes.index):
        raise ValueError("forecasts and outcomes are not aligned on the same index")
    values = probabilities.to_numpy(dtype=float)
    if np.isnan(values).any() or (values < 0).any() or not np.allclose(values.sum(axis=1), 1.0):
        raise ValueError("every forecast row must be non-negative and sum to 1")
    if not outcomes.isin(OUTCOMES).all():
        raise ValueError("outcomes must all be H, D or A")


def one_hot(outcomes: pd.Series) -> np.ndarray:
    """Indicator matrix of the observed outcomes, columns in OUTCOMES order."""
    return (outcomes.to_numpy(dtype=str)[:, None] == np.array(OUTCOMES)).astype(float)


def log_losses(probabilities: pd.DataFrame, outcomes: pd.Series) -> pd.Series:
    """Per match: negative natural log of the probability given to what happened.

    Not clipped: a forecast that gave the observed outcome zero probability scores infinity.
    """
    check_forecasts(probabilities, outcomes)
    observed = (probabilities.to_numpy(dtype=float) * one_hot(outcomes)).sum(axis=1)
    with np.errstate(divide="ignore"):
        return pd.Series(-np.log(observed), index=probabilities.index)


def log_loss(probabilities: pd.DataFrame, outcomes: pd.Series) -> float:
    """Mean of log_losses over the matches."""
    return float(log_losses(probabilities, outcomes).mean())


def ranked_probability_score(probabilities: pd.DataFrame, outcomes: pd.Series) -> float:
    """Mean RPS over the ordered outcomes H, D, A: 0 is a perfect forecast, 1 the worst possible.

    Compares cumulative forecast and observed distributions, so putting probability on a
    draw costs less than putting it on an away win when the home side won.
    """
    check_forecasts(probabilities, outcomes)
    gaps = np.cumsum(probabilities.to_numpy(dtype=float), axis=1) - np.cumsum(one_hot(outcomes), axis=1)
    return float((gaps[:, :-1] ** 2).sum(axis=1).mean() / (len(OUTCOMES) - 1))


def accuracy(probabilities: pd.DataFrame, outcomes: pd.Series) -> float:
    """Share of matches where the most probable outcome happened; ties go to the first in H, D, A."""
    check_forecasts(probabilities, outcomes)
    predicted = np.array(OUTCOMES)[probabilities.to_numpy(dtype=float).argmax(axis=1)]
    return float((predicted == outcomes.to_numpy(dtype=str)).mean())
