"""EWMA form for v2 and v2-pre (docs/v2_lineup_plan.md amendment A1).

points_ewma: per team, the exponentially weighted mean of league points (3, 1, 0) over the team's
earlier matches in the spell: pandas ewm(span=5, adjust=True, min_periods=3) applied after shift(1),
so a match never counts toward its own value. Windows cross seasons within a spell, as in v1. Enters
as home_points_ewma, away_points_ewma and points_ewma_diff. ewma_points is module-level so that
leakage checks can replace it with a planted leak.
"""

import pandas as pd

from src.features import MIN_PERIODS, TEAM, differences, long_table, side

SPAN = 5
NAME = "points_ewma"


def ewma_points(long: pd.DataFrame) -> pd.Series:
    """Per long-table row: the EWMA of the team's points before the match."""
    return long.groupby(TEAM)["points"].transform(
        lambda history: history.shift(1).ewm(span=SPAN, adjust=True, min_periods=MIN_PERIODS).mean())


def build_ewma_features(matches: pd.DataFrame) -> pd.DataFrame:
    """home_points_ewma, away_points_ewma and points_ewma_diff, indexed like `matches`."""
    long = long_table(matches)
    per_team = pd.DataFrame({NAME: ewma_points(long), "match": long["match"], "venue": long["venue"]})
    home, away = side(per_team, "home"), side(per_team, "away")
    return pd.concat([home, away, differences(home, away)], axis=1).reindex(matches.index)


def ewma_points_including_this_match(long: pd.DataFrame) -> pd.Series:
    """PLANTED LEAK: the EWMA includes the match's own points (no shift(1))."""
    return long.groupby(TEAM)["points"].transform(
        lambda history: history.ewm(span=SPAN, adjust=True, min_periods=MIN_PERIODS).mean())
