"""Bookmaker decimal odds to outcome probabilities."""

import pandas as pd

from src.data import ODDS_COLUMNS
from src.metrics import OUTCOMES


def implied_probabilities(matches: pd.DataFrame) -> pd.DataFrame:
    """H/D/A probabilities from 1/odds, normalised per match so they sum to 1.

    Normalising removes the bookmaker's overround (the margin that makes 1/odds sum
    above 1) in proportion to each price.
    """
    inverse = 1.0 / matches[ODDS_COLUMNS].to_numpy(dtype=float)
    probabilities = inverse / inverse.sum(axis=1, keepdims=True)
    return pd.DataFrame(probabilities, index=matches.index, columns=OUTCOMES)
