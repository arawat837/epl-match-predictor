"""Pre-match Elo ratings, updated date by date.

Every match on a date is rated from the state before that date, and the updates are
applied only once the whole date is done, so no same-day result leaks into another
match's rating. New teams start at `initial_rating`; a team returning after relegation
resumes the rating it left with.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EloParams:
    k: float = 20.0
    home_advantage: float = 60.0  # rating points added to the home side's expectation
    initial_rating: float = 1500.0


def goal_difference_multiplier(goal_difference: int) -> float:
    """World Football Elo margin weight: 1 up to a one-goal margin, 1.5 for two, (11 + n) / 8 beyond."""
    margin = abs(goal_difference)
    if margin <= 1:
        return 1.0
    if margin == 2:
        return 1.5
    return (11 + margin) / 8


def expected_home_score(home_rating: float, away_rating: float, home_advantage: float) -> float:
    """Expected points share for the home side (win 1, draw 0.5)."""
    return 1 / (1 + 10 ** ((away_rating - home_rating - home_advantage) / 400))


def home_score(home_goals: int, away_goals: int) -> float:
    """Actual points share for the home side: 1 win, 0.5 draw, 0 loss."""
    return 1.0 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0.0


def rating_change(home_rating: float, away_rating: float, home_goals: int, away_goals: int,
                  params: EloParams) -> float:
    """Points the home side gains (the away side loses the same)."""
    surprise = home_score(home_goals, away_goals) - expected_home_score(
        home_rating, away_rating, params.home_advantage)
    return params.k * goal_difference_multiplier(home_goals - away_goals) * surprise


def pre_match_elo(matches: pd.DataFrame, params: EloParams = EloParams()) -> pd.DataFrame:
    """home_elo, away_elo and elo_diff before each match, indexed like `matches`.

    A match without a score (not yet played) gets ratings but changes nothing.
    """
    ratings: dict[str, float] = {}
    pre_match: dict[object, tuple[float, float]] = {}
    for _, day in matches.groupby("date", sort=True):
        after_day: dict[str, float] = {}
        for match in day.itertuples():
            home = ratings.get(match.home, params.initial_rating)
            away = ratings.get(match.away, params.initial_rating)
            pre_match[match.Index] = (home, away)
            if pd.isna(match.FTHG) or pd.isna(match.FTAG):
                continue
            change = rating_change(home, away, int(match.FTHG), int(match.FTAG), params)
            after_day[match.home], after_day[match.away] = home + change, away - change
        ratings.update(after_day)
    elo = pd.DataFrame.from_dict(pre_match, orient="index", columns=["home_elo", "away_elo"])
    elo = elo.reindex(matches.index)
    return elo.assign(elo_diff=elo["home_elo"] - elo["away_elo"])
