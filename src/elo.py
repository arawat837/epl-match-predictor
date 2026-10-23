"""Pre-match Elo ratings.

Matches are processed in date order. For each match both pre-match ratings are stored
first, then updated. At each season change, every team that played in the previous
season regresses toward 1500 by `carryover`; any team not in the previous season's data
(promoted or returning) starts at `promoted_start`. In the first season everyone starts
at `start`.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EloParams:
    K: float = 20.0
    home_adv: float = 80.0
    start: float = 1500.0
    promoted_start: float = 1450.0
    carryover: float = 0.75


def expected_home(r_home: float, r_away: float, home_adv: float) -> float:
    """Expected score of the home side."""
    return 1 / (1 + 10 ** ((r_away - (r_home + home_adv)) / 400))


def actual_score(home_goals: int, away_goals: int) -> float:
    """1 for a home win, 0.5 for a draw, 0 for an away win."""
    return 1.0 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0.0


def goal_difference_multiplier(goal_difference: int) -> float:
    """g: 1 if |GD| <= 1, 1.5 if |GD| == 2, (11 + |GD|) / 8 if |GD| >= 3."""
    margin = abs(goal_difference)
    if margin <= 1:
        return 1.0
    if margin == 2:
        return 1.5
    return (11 + margin) / 8


def update(r_home: float, r_away: float, home_goals: int, away_goals: int,
           params: EloParams) -> tuple[float, float]:
    """Ratings after the match: delta = K * g * (actual - expected_home)."""
    g = goal_difference_multiplier(home_goals - away_goals)
    delta = params.K * g * (actual_score(home_goals, away_goals) - expected_home(r_home, r_away, params.home_adv))
    return r_home + delta, r_away - delta


def regress(ratings: dict[str, float], previous_season_teams: set[str], params: EloParams) -> dict[str, float]:
    """Season change: last season's teams move toward 1500; all others are dropped,
    so they re-enter at promoted_start."""
    return {team: params.start + params.carryover * (ratings[team] - params.start)
            for team in previous_season_teams}


def run_elo(matches: pd.DataFrame, params: EloParams = EloParams()) -> tuple[pd.DataFrame, dict[str, float]]:
    """Pre-match ratings for every match, and every team's rating after the last match."""
    ratings: dict[str, float] = {}
    newcomer = params.start
    season, season_teams = None, set()
    pre_match: dict[object, tuple[float, float]] = {}
    for match in matches.sort_values("date", kind="stable").itertuples():
        if match.season != season:
            if season is not None:
                ratings = regress(ratings, season_teams, params)
                newcomer = params.promoted_start
            season, season_teams = match.season, set()
        season_teams |= {match.home, match.away}
        r_home = ratings.setdefault(match.home, newcomer)
        r_away = ratings.setdefault(match.away, newcomer)
        pre_match[match.Index] = (r_home, r_away)
        ratings[match.home], ratings[match.away] = update(r_home, r_away, match.FTHG, match.FTAG, params)
    elo = pd.DataFrame.from_dict(pre_match, orient="index", columns=["elo_home", "elo_away"])
    elo = elo.reindex(matches.index)
    return elo.assign(elo_diff=elo["elo_home"] - elo["elo_away"]), ratings


def pre_match_elo(matches: pd.DataFrame, params: EloParams = EloParams()) -> pd.DataFrame:
    """elo_home, elo_away and elo_diff before each match, indexed like `matches`."""
    return run_elo(matches, params)[0]


def final_ratings(matches: pd.DataFrame, params: EloParams = EloParams()) -> pd.Series:
    """Ratings after the last match for the teams in the last season, highest first."""
    last_season = matches["season"].max()
    teams = set(matches.loc[matches["season"] == last_season, ["home", "away"]].stack())
    ratings = run_elo(matches, params)[1]
    return pd.Series({team: ratings[team] for team in teams}).sort_values(ascending=False)
