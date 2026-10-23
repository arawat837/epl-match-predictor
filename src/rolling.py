"""Per-team running statistics from earlier matches only.

Each match becomes two team appearances, one per side. A statistic for an appearance
uses only that team's earlier appearances: windows are shifted by one, and a team never
plays twice on one date, so "earlier" means strictly earlier dates.

History runs within a spell of consecutive Premier League seasons. A team coming back
after a season or more away starts a new spell, so its form isn't taken from years ago.
A statistic with no earlier match in the spell is missing (NaN), never backfilled.
"""

import numpy as np
import pandas as pd

from src.seasons import season_label, season_start

SIDE_COLUMNS = {
    "home": {"home": "team", "away": "opponent", "FTHG": "goals_for", "FTAG": "goals_against",
             "HS": "shots_for", "AS": "shots_against", "HST": "sot_for", "AST": "sot_against"},
    "away": {"away": "team", "home": "opponent", "FTAG": "goals_for", "FTHG": "goals_against",
             "AS": "shots_for", "HS": "shots_against", "AST": "sot_for", "HST": "sot_against"},
}
STAT_COLUMNS = ["goals_for", "goals_against", "shots_for", "shots_against", "sot_for", "sot_against"]
TEAM = ["team", "spell"]
TEAM_AT_VENUE = ["team", "spell", "venue"]


def side_appearances(matches: pd.DataFrame, venue: str) -> pd.DataFrame:
    """One appearance per match for the team on `venue`'s side, stats from its point of view."""
    columns = SIDE_COLUMNS[venue]
    side = matches[["date", "season", *columns]].rename(columns=columns)
    return side.assign(match=matches.index, venue=venue)


def match_points(goals_for: pd.Series, goals_against: pd.Series) -> pd.Series:
    """League points: 3 win, 1 draw, 0 loss; missing if the score is."""
    return np.sign(goals_for - goals_against).map({1.0: 3.0, 0.0: 1.0, -1.0: 0.0})


def check_one_match_per_day(appearances: pd.DataFrame) -> None:
    """Raise if a team plays twice on one date, which would make 'earlier' ambiguous."""
    if appearances.duplicated(subset=["team", "date"]).any():
        raise ValueError("a team has two matches on one date")


def spell_ids(appearances: pd.DataFrame) -> pd.Series:
    """Number each team's runs of consecutive seasons (appearances sorted by team, date)."""
    gap = appearances["season"].map(season_start).groupby(appearances["team"]).diff() > 1
    return gap.groupby(appearances["team"]).cumsum()


def team_appearances(matches: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match, sorted by team then date, with points and spell."""
    appearances = pd.concat([side_appearances(matches, "home"), side_appearances(matches, "away")],
                            ignore_index=True)
    check_one_match_per_day(appearances)
    appearances = appearances.astype({column: "float64" for column in STAT_COLUMNS})
    appearances["points"] = match_points(appearances["goals_for"], appearances["goals_against"])
    appearances = appearances.sort_values(["team", "date"], kind="stable", ignore_index=True)
    return appearances.assign(spell=spell_ids(appearances))


def rolling_mean(appearances: pd.DataFrame, column: str, window: int, keys: list[str]) -> pd.Series:
    """Mean of `column` over each group's previous `window` appearances, current one excluded."""
    groups = [appearances[key] for key in keys]
    previous = appearances[column].groupby(groups).shift(1)
    means = previous.groupby(groups).rolling(window, min_periods=1).mean()
    return means.reset_index(level=list(range(len(keys))), drop=True).reindex(appearances.index)


def days_since_last_match(appearances: pd.DataFrame) -> pd.Series:
    """Days since the team's previous match in the same spell."""
    return appearances.groupby(TEAM)["date"].diff().dt.days.astype("float64")


def pre_season_prior(appearances: pd.DataFrame, promoted_prior_ppg: float) -> pd.Series:
    """Per appearance: the team's points per game over last season, the promoted-side
    default if it wasn't in the league, or missing when last season isn't in the data."""
    last_season_ppg = appearances.groupby(["team", "season"])["points"].mean()
    previous = appearances["season"].map(lambda season: season_label(season_start(season) - 1))
    lookup = pd.MultiIndex.from_arrays([appearances["team"], previous])
    prior = pd.Series(last_season_ppg.reindex(lookup).to_numpy(), index=appearances.index)
    promoted = prior.isna() & previous.isin(set(appearances["season"]))
    return prior.mask(promoted, promoted_prior_ppg)


def season_points_per_game(appearances: pd.DataFrame, carryover_matches: float,
                           promoted_prior_ppg: float) -> pd.Series:
    """Points per game so far this season, shrunk toward last season's.

    (points so far + carryover_matches * prior) / (games so far + carryover_matches),
    so the prior dominates early and fades as the season goes on. With no prior (first
    season in the data) it is plain points per game, missing before the first match.
    """
    by_season = appearances.groupby(["team", "season"])["points"]
    points_so_far = by_season.transform(lambda points: points.shift(1, fill_value=0.0).cumsum())
    games_so_far = by_season.cumcount()
    prior = pre_season_prior(appearances, promoted_prior_ppg)
    weight = prior.notna() * carryover_matches
    return (points_so_far + weight * prior.fillna(0.0)) / (games_so_far + weight)
