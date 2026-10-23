"""Reference forecasts every model is compared against.

Each baseline is a Predictor: (train, test) -> H/D/A probabilities for the test matches.
"""

import pandas as pd

from src.evaluate import Predictor
from src.metrics import OUTCOMES
from src.odds import implied_probabilities


def constant_forecast(index: pd.Index, probabilities: list[float]) -> pd.DataFrame:
    """The same H/D/A forecast for every match."""
    return pd.DataFrame([probabilities] * len(index), index=index, columns=OUTCOMES)


def uniform(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """1/3 on each outcome."""
    return constant_forecast(test.index, [1 / 3, 1 / 3, 1 / 3])


def always_home(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Certainty of a home win."""
    return constant_forecast(test.index, [1.0, 0.0, 0.0])


def base_rate(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Outcome frequencies over all training matches."""
    frequencies = train["result"].value_counts(normalize=True).reindex(OUTCOMES, fill_value=0.0)
    return constant_forecast(test.index, frequencies.tolist())


def bookmaker(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Pre-match bookmaker odds with the overround removed."""
    return implied_probabilities(test)


BASELINES: dict[str, Predictor] = {
    "uniform": uniform,
    "always home": always_home,
    "base rate": base_rate,
    "bookmaker": bookmaker,
}
