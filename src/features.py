"""Pre-match feature table: one row per match, built only from earlier matches.

Columns are prefixed home_/away_ for the team they describe:
- Elo before the match, plus elo_diff (home minus away, without home advantage)
- form over the last N matches: points per game (ppg), goals for (gf) and against (ga),
  overall and at this match's venue (_home_only for the home side, _away_only for the away side)
- shots and shots on target, for and against, averaged over the last N matches
- days_rest: days since the team's previous match
- season_ppg: points per game this season, carried over from last season early on
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import FEATURES_PATH
from src.elo import EloParams, pre_match_elo
from src.rolling import (
    TEAM,
    TEAM_AT_VENUE,
    days_since_last_match,
    rolling_mean,
    season_points_per_game,
    team_appearances,
)

KEY_COLUMNS = ["date", "season", "home", "away"]
FORM_STATS = {"ppg": "points", "gf": "goals_for", "ga": "goals_against"}
SHOT_STATS = ["shots_for", "shots_against", "sot_for", "sot_against"]


@dataclass(frozen=True)
class FeatureParams:
    elo: EloParams = field(default_factory=EloParams)
    windows: tuple[int, ...] = (5, 10)
    carryover_matches: float = 5.0  # weight of last season's ppg, in matches
    promoted_prior_ppg: float = 1.0  # pre-season ppg for a side that wasn't in the league


def window_features(appearances: pd.DataFrame, window: int) -> dict[str, pd.Series]:
    """Form and shot averages over the previous `window` matches for each appearance."""
    columns = {}
    for name, stat in FORM_STATS.items():
        columns[f"{name}_last{window}"] = rolling_mean(appearances, stat, window, TEAM)
        columns[f"{name}_last{window}_venue"] = rolling_mean(appearances, stat, window, TEAM_AT_VENUE)
    for stat in SHOT_STATS:
        columns[f"{stat}_last{window}"] = rolling_mean(appearances, stat, window, TEAM)
    return columns


def appearance_features(appearances: pd.DataFrame, params: FeatureParams) -> pd.DataFrame:
    """Every per-team feature for each appearance, before the home_/away_ prefix."""
    columns: dict[str, pd.Series] = {}
    for window in params.windows:
        columns |= window_features(appearances, window)
    columns["days_rest"] = days_since_last_match(appearances)
    columns["season_ppg"] = season_points_per_game(
        appearances, params.carryover_matches, params.promoted_prior_ppg)
    return pd.DataFrame(columns).assign(match=appearances["match"], venue=appearances["venue"])


def side_features(per_appearance: pd.DataFrame, venue: str) -> pd.DataFrame:
    """One side's features keyed by match, e.g. ppg_last5_venue -> home_ppg_last5_home_only."""
    side = per_appearance[per_appearance["venue"] == venue].set_index("match").drop(columns="venue")
    return side.rename(columns=lambda name: f"{venue}_{name.replace('_venue', f'_{venue}_only')}")


def build_features(matches: pd.DataFrame, params: FeatureParams = FeatureParams()) -> pd.DataFrame:
    """Feature table indexed like `matches`: KEY_COLUMNS, then every pre-match feature."""
    per_appearance = appearance_features(team_appearances(matches), params)
    return pd.concat([
        matches[KEY_COLUMNS],
        pre_match_elo(matches, params.elo),
        side_features(per_appearance, "home"),
        side_features(per_appearance, "away"),
    ], axis=1)


def feature_columns(features: pd.DataFrame) -> list[str]:
    """The model inputs: every column except the match keys."""
    return [column for column in features.columns if column not in KEY_COLUMNS]


def save_features(features: pd.DataFrame, path: Path = FEATURES_PATH) -> Path:
    """Write the feature table to parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(path, index=False)
    return path
