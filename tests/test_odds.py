import pandas as pd
import pytest

from src.odds import implied_probabilities


def odds(home: float, draw: float, away: float) -> pd.DataFrame:
    return pd.DataFrame({"odds_home": [home], "odds_draw": [draw], "odds_away": [away]})


def test_fair_odds_give_their_reciprocals():
    assert implied_probabilities(odds(2.0, 4.0, 4.0)).iloc[0].tolist() == [0.5, 0.25, 0.25]


def test_overround_is_removed_in_proportion_to_each_price():
    probabilities = implied_probabilities(odds(1.9, 3.6, 4.2)).iloc[0]
    assert (1 / 1.9 + 1 / 3.6 + 1 / 4.2) > 1  # the bookmaker's margin
    assert probabilities.sum() == pytest.approx(1)
    assert probabilities["H"] / probabilities["D"] == pytest.approx(3.6 / 1.9)
