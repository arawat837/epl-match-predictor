"""Pre-match feature table: one row per match, built only from earlier matches.

- Elo: elo_home, elo_away, elo_diff (src/elo.py).
- Per team, from a long table of one row per team per match, grouped by team and sorted
  by date, with shift(1) before rolling (min_periods=3, NaN otherwise; windows cross
  season boundaries, but a gap of more than 200 days since the team's previous match
  starts a new spell, and history never reaches across spells):
  - last 5 and last 10 matches, all venues: mean points, goals for (gf), goals against (ga),
    shots for, shots against, shots on target for (sot_for)
  - last 5 matches at this match's venue (home matches for the home team, away matches for
    the away team): mean points, gf, ga
  - days_rest: days since the team's previous match, capped at 14 (NaN for the first match
    of a spell)
  - season_ppg: (5 * last_season_ppg + points_so_far) / (5 + games_so_far); last_season_ppg
    is 1.0 for promoted teams, teams starting a new spell, and every team in the first season
- Each per-team feature appears as home_X, away_X and X_diff (home minus away).
- burn_in flags the first season in the data; it is kept, not dropped.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import FEATURES_PATH
from src.elo import EloParams, pre_match_elo
from src.seasons import season_label, season_start

LONG_COLUMNS = {
    "home": {"home": "team", "FTHG": "goals_for", "FTAG": "goals_against",
             "HS": "shots", "HST": "shots_on_target", "AS": "shots_against"},
    "away": {"away": "team", "FTAG": "goals_for", "FTHG": "goals_against",
             "AS": "shots", "AST": "shots_on_target", "HS": "shots_against"},
}
STAT_COLUMNS = ["goals_for", "goals_against", "shots", "shots_on_target", "shots_against"]
ALL_VENUE_STATS = {"points": "points", "gf": "goals_for", "ga": "goals_against",
                   "shots_for": "shots", "shots_against": "shots_against", "sot_for": "shots_on_target"}
VENUE_STATS = {"points": "points", "gf": "goals_for", "ga": "goals_against"}
WINDOWS = (5, 10)
VENUE_WINDOW = 5
MIN_PERIODS = 3
REST_CAP_DAYS = 14
PRIOR_GAMES = 5
PROMOTED_PPG = 1.0
NEW_SPELL_GAP_DAYS = 200  # summer breaks are under ~150 days; a missed season is far longer
TEAM = ["team", "spell"]
KEY_COLUMNS = ["date", "season", "home", "away", "burn_in"]


def points(goals_for: pd.Series, goals_against: pd.Series) -> pd.Series:
    """League points: 3 for a win, 1 for a draw, 0 for a loss."""
    return pd.Series(np.select([goals_for > goals_against, goals_for == goals_against], [3.0, 1.0], 0.0),
                     index=goals_for.index)


def long_table(matches: pd.DataFrame) -> pd.DataFrame:
    """One row per team per match, from that team's point of view, sorted by team then date."""
    sides = [matches[["date", "season", *columns]].rename(columns=columns).assign(match=matches.index, venue=venue)
             for venue, columns in LONG_COLUMNS.items()]
    long = pd.concat(sides, ignore_index=True).astype({column: "float64" for column in STAT_COLUMNS})
    long["points"] = points(long["goals_for"], long["goals_against"])
    long = long.sort_values(["team", "date"], kind="stable", ignore_index=True)
    return long.assign(spell=spells(long))


def spells(long: pd.DataFrame) -> pd.Series:
    """Number each team's spells (long table sorted by team, date): a gap of more than
    200 days since the team's previous match starts a new one."""
    gap = long.groupby("team")["date"].diff().dt.days > NEW_SPELL_GAP_DAYS
    return gap.groupby(long["team"]).cumsum()


def rolling_mean(long: pd.DataFrame, column: str, window: int, keys: list[str]) -> pd.Series:
    """Mean of `column` over each group's previous `window` rows: shift(1) before rolling."""
    return long.groupby(keys)[column].transform(
        lambda history: history.shift(1).rolling(window, min_periods=MIN_PERIODS).mean())


def days_rest(long: pd.DataFrame) -> pd.Series:
    """Days since the team's previous match in the same spell, capped at 14."""
    return long.groupby(TEAM)["date"].diff().dt.days.clip(upper=REST_CAP_DAYS).astype("float64")


def previous_season(season: str) -> str:
    """Label of the season before, e.g. "2006-07" -> "2005-06"."""
    return season_label(season_start(season) - 1)


def last_season_ppg(long: pd.DataFrame) -> pd.Series:
    """Per row: the team's final points per game last season in the same spell, or 1.0 if it has none."""
    final = long.groupby([*TEAM, "season"])["points"].mean()
    lookup = pd.MultiIndex.from_arrays([long["team"], long["spell"], long["season"].map(previous_season)])
    return pd.Series(final.reindex(lookup).to_numpy(), index=long.index).fillna(PROMOTED_PPG)


def season_ppg(long: pd.DataFrame) -> pd.Series:
    """(5 * last_season_ppg + points_so_far) / (5 + games_so_far), before the match."""
    by_season = long.groupby(["team", "season"])["points"]
    points_so_far = by_season.transform(lambda season_points: season_points.shift(1, fill_value=0.0).cumsum())
    games_so_far = by_season.cumcount()
    return (PRIOR_GAMES * last_season_ppg(long) + points_so_far) / (PRIOR_GAMES + games_so_far)


def team_features(long: pd.DataFrame) -> pd.DataFrame:
    """Every per-team feature for each row of the long table, plus its match and venue."""
    columns: dict[str, pd.Series] = {}
    for window in WINDOWS:
        for name, stat in ALL_VENUE_STATS.items():
            columns[f"{name}_last{window}"] = rolling_mean(long, stat, window, TEAM)
    for name, stat in VENUE_STATS.items():
        columns[f"{name}_venue_last{VENUE_WINDOW}"] = rolling_mean(long, stat, VENUE_WINDOW, [*TEAM, "venue"])
    columns["days_rest"] = days_rest(long)
    columns["season_ppg"] = season_ppg(long)
    return pd.DataFrame(columns).assign(match=long["match"], venue=long["venue"])


def side(per_team: pd.DataFrame, venue: str) -> pd.DataFrame:
    """One side's features indexed by match, prefixed home_ or away_."""
    rows = per_team[per_team["venue"] == venue].set_index("match").drop(columns="venue")
    return rows.add_prefix(f"{venue}_")


def differences(home: pd.DataFrame, away: pd.DataFrame) -> pd.DataFrame:
    """X_diff = home_X - away_X for every per-team feature."""
    names = [column.removeprefix("home_") for column in home.columns]
    values = home.to_numpy() - away.loc[home.index].to_numpy()
    return pd.DataFrame(values, index=home.index, columns=[f"{name}_diff" for name in names])


def build_features(matches: pd.DataFrame, elo_params: EloParams = EloParams()) -> pd.DataFrame:
    """Feature table indexed like `matches`: KEY_COLUMNS, then every pre-match feature."""
    per_team = team_features(long_table(matches))
    home, away = side(per_team, "home"), side(per_team, "away")
    keys = matches[KEY_COLUMNS[:-1]].assign(burn_in=matches["season"] == matches["season"].min())
    return pd.concat([keys, pre_match_elo(matches, elo_params), home, away, differences(home, away)], axis=1)


def feature_columns(features: pd.DataFrame) -> list[str]:
    """The model inputs: every column except the match keys and the burn-in flag."""
    return [column for column in features.columns if column not in KEY_COLUMNS]


def save_features(features: pd.DataFrame, path: Path = FEATURES_PATH) -> Path:
    """Write the feature table to parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(path, index=False)
    return path
