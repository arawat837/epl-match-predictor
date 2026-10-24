"""Leakage checks and the planted leaks that prove they can fail.

A check rebuilds a match's values from rows dated strictly before it, plus the match's own
rows with every value replaced by one that differs from the real value (for match stats, the
result is flipped as well), and flags the match if the rebuilt values differ from the stored
ones. For a planted leak, the leaky code builds both the stored table and the rebuild, as if the
leak were in src/; the real code is never changed on disk.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from types import ModuleType

import numpy as np
import pandas as pd

import src.elo as elo
import src.features as features
from src.availability import build_availability
from src.availability_features import build_availability_features
from src.features import MIN_PERIODS, NEW_SPELL_GAP_DAYS, REST_CAP_DAYS, build_features, feature_columns
from src.fpl import load_fpl
from src.name_maps import link_rows, load_overrides, team_name_map

MATCH_KEY = ["date", "home", "away"]
SCRAMBLED_SHOTS = {"HS": 99, "AS": 99, "HST": 99, "AST": 99}  # no real match has 99 shots
IMPOSSIBLE = {"minutes": 9999, "yellow_cards": 9, "red_cards": 9, "bps": 999, "ict_index": 999.0, "price": 999.0}
LIST_COLUMNS = ["banned_red", "banned_yellow", "key_players"]


@contextmanager
def planted(module: ModuleType, name: str, leaky: Callable) -> Iterator[None]:
    """Replace `module.name` with a leaky version until the block ends."""
    original = getattr(module, name)
    setattr(module, name, leaky)
    try:
        yield
    finally:
        setattr(module, name, original)


# ---------- Stage 4 features ----------

def scrambled_stats(home_goals: int, away_goals: int) -> dict[str, object]:
    """Stats for a match's own row that differ from the real ones in every column. The result is
    flipped, so both sides' points change: an away win becomes a home win (away goals + 9 to 0),
    a home win becomes an away win (0 to home goals + 9) and a draw d-d becomes d+1 to d+9. Both
    goal counts differ from the real ones, and shots are 99."""
    if away_goals > home_goals:
        goals, result = (away_goals + 9, 0), "H"
    elif home_goals > away_goals:
        goals, result = (0, home_goals + 9), "A"
    else:
        goals, result = (home_goals + 1, home_goals + 9), "A"
    return {"FTHG": goals[0], "FTAG": goals[1], "result": result, **SCRAMBLED_SHOTS}


def earlier_plus_scrambled(matches: pd.DataFrame, target: int) -> pd.DataFrame:
    """Every match dated strictly before `target`, then `target` with its own stats scrambled."""
    match = matches.loc[[target]].copy()
    real = match.loc[target]
    for column, value in scrambled_stats(int(real["FTHG"]), int(real["FTAG"])).items():
        match.loc[target, column] = value
    earlier = matches[matches["date"] < match.loc[target, "date"]]
    return pd.concat([earlier, match])


def stored_like(matches: pd.DataFrame, stored: pd.DataFrame) -> pd.DataFrame:
    """A stored feature table looked up by match key and indexed like `matches`."""
    keys = pd.MultiIndex.from_frame(matches[MATCH_KEY])
    return stored.set_index(MATCH_KEY).loc[keys].set_axis(matches.index)


def features_differ(rebuilt: pd.Series, stored: pd.Series) -> bool:
    """Whether any feature differs beyond a relative 1e-9 (NaN equals NaN)."""
    rebuilt, stored = rebuilt.astype(float), stored.astype(float)
    same = (rebuilt - stored).abs().le(1e-9 * stored.abs().clip(lower=1)) | (rebuilt.isna() & stored.isna())
    return bool((~same).any())


def flagged_features(matches: pd.DataFrame, full: pd.DataFrame, targets: list[int]) -> int:
    """How many targets' rebuilt features differ from `full` (a feature table indexed like matches)."""
    columns = feature_columns(full)
    return sum(features_differ(build_features(earlier_plus_scrambled(matches, target)).loc[target, columns],
                               full.loc[target, columns]) for target in targets)


def unshifted_rolling_mean(long: pd.DataFrame, column: str, window: int, keys: list[str]) -> pd.Series:
    """PLANTED LEAK: the window includes the match itself (no shift(1))."""
    return long.groupby(keys)[column].transform(lambda history: history.rolling(window, min_periods=MIN_PERIODS).mean())


def rest_until_next_match(long: pd.DataFrame) -> pd.Series:
    """PLANTED LEAK: days until the team's next match instead of since its previous one."""
    return (-long.groupby(features.TEAM)["date"].diff(-1)).dt.days.clip(upper=REST_CAP_DAYS).astype("float64")


def season_ppg_including_this_match(long: pd.DataFrame) -> pd.Series:
    """PLANTED LEAK: season points per game counting the match's own points."""
    by_season = long.groupby(["team", "season"])["points"]
    return by_season.cumsum() / (by_season.cumcount() + 1)


def post_update_elo(matches: pd.DataFrame, params: elo.EloParams = elo.EloParams()) -> pd.DataFrame:
    """PLANTED LEAK: ratings after the match's own update instead of before it."""
    pre = elo.pre_match_elo(matches, params)
    post = [elo.update(home, away, home_goals, away_goals, params) for home, away, home_goals, away_goals
            in zip(pre["elo_home"], pre["elo_away"], matches["FTHG"], matches["FTAG"])]
    ratings = pd.DataFrame(post, index=matches.index, columns=["elo_home", "elo_away"])
    return ratings.assign(elo_diff=ratings["elo_home"] - ratings["elo_away"])


def spells_from_gap_to_next_match(long: pd.DataFrame) -> pd.Series:
    """PLANTED LEAK: a spell break read from the gap to the team's next match."""
    gap_after = (-long.groupby("team")["date"].diff(-1)).dt.days > NEW_SPELL_GAP_DAYS
    return gap_after.groupby(long["team"]).cumsum()


# ---------- Stage 7 and 8 availability ----------

def linked_fpl_rows(matches: pd.DataFrame) -> pd.DataFrame:
    """The FPL archive's player rows linked to matches."""
    rows = load_fpl()
    names = team_name_map(list(rows["fpl_team"].unique()), load_overrides())
    return link_rows(rows, matches, dict(zip(names["fpl_name"], names["canonical"])))


def earlier_rows_plus_scrambled(linked: pd.DataFrame, matches: pd.DataFrame,
                                target: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rows and matches dated strictly before the target, plus the target's rows with impossible
    values (only who is listed survives, as the squad list as of that date)."""
    match = matches.loc[target]
    own = linked[(linked["date"] == match["date"]) & (linked["home"] == match["home"])
                 & (linked["away"] == match["away"])].assign(**IMPOSSIBLE)
    rows = pd.concat([linked[linked["date"] < match["date"]], own])
    return rows, pd.concat([matches[matches["date"] < match["date"]], matches.loc[[target]]])


def differing(rebuilt: pd.Series, expected: pd.Series) -> list[str]:
    """Columns whose rebuilt value differs from the expected one."""
    different = []
    for column, value in expected.items():
        got = rebuilt[column]
        if any(column.endswith(name) for name in LIST_COLUMNS):
            same = list(got) == list(value)
        elif isinstance(value, (int, float, np.number)) and not isinstance(value, bool):
            same = (pd.isna(got) and pd.isna(value)) or np.isclose(float(got), float(value), rtol=1e-9)
        else:
            same = got == value
        if not same:
            different.append(column)
    return different


def rebuild_availability(linked: pd.DataFrame, matches: pd.DataFrame, target: int) -> pd.Series:
    rows, earlier = earlier_rows_plus_scrambled(linked, matches, target)
    return build_availability(rows, earlier, only=[target]).loc[target]


def rebuild_stage8(linked: pd.DataFrame, matches: pd.DataFrame, target: int) -> pd.Series:
    rows, earlier = earlier_rows_plus_scrambled(linked, matches, target)
    return build_availability_features(rows, earlier, only=[target]).loc[target]


def flagged_availability(linked: pd.DataFrame, matches: pd.DataFrame, targets: list[int]) -> int:
    """How many targets the Stage 7 check flags, with the stored table built by the same code."""
    full = build_availability(linked, matches, only=targets)
    return sum(bool(differing(rebuild_availability(linked, matches, target), full.loc[target])) for target in targets)


def flagged_stage8(linked: pd.DataFrame, matches: pd.DataFrame, targets: list[int]) -> int:
    """How many targets the Stage 8 check flags, with the stored table built by the same code."""
    full = build_availability_features(linked, matches, only=targets)
    return sum(bool(differing(rebuild_stage8(linked, matches, target), full.loc[target])) for target in targets)


def own_match_included(schedule: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    """PLANTED LEAK: the team's matches up to and including `date`."""
    return schedule[schedule["date"] <= date]


def every_snapshot(dates: np.ndarray, date: np.datetime64) -> int:
    """PLANTED LEAK: every price snapshot, including those dated after the match."""
    return len(dates)


def absence_from_this_match(prior: pd.DataFrame, date: pd.Timestamp) -> pd.Timestamp:
    """PLANTED LEAK: absence read from match t's own minutes instead of t-1's."""
    return date


def spells_unavailable_including_same_day(spells: pd.DataFrame, date: pd.Timestamp) -> set[object]:
    """PLANTED LEAK: an injury spell starting on the match date counts as unavailable."""
    started = spells["start"] <= date
    return set(spells.loc[started & (spells["end"].isna() | (spells["end"] > date)), "player"])
