"""Walk-forward season splits and the holdout guard.

The holdout season (config.HOLDOUT_SEASON) stays locked until the user releases it:
load_evaluation_matches never reads it, and walk_forward_splits refuses any table that
contains it. Seasons after the holdout are never evaluated, locked or not.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import FIRST_TEST_SEASON, HOLDOUT_SEASON, MATCHES_PATH


class HoldoutLockedError(RuntimeError):
    """Raised when evaluation reaches a season it must not see."""


@dataclass(frozen=True)
class Fold:
    """One walk-forward step: fit on `train`, score on `test` (a single season)."""

    season: str
    train: pd.DataFrame
    test: pd.DataFrame


def load_evaluation_matches(path: Path = MATCHES_PATH, unlock_holdout: bool = False) -> pd.DataFrame:
    """Matches allowed in evaluation, filtered at read time so locked seasons never load.

    Locked: every season before the holdout. Unlocked: up to and including the holdout.
    """
    operator = "<=" if unlock_holdout else "<"
    return pd.read_parquet(path, filters=[("season", operator, HOLDOUT_SEASON)])


def check_holdout(matches: pd.DataFrame, unlock_holdout: bool) -> None:
    """Raise if `matches` holds the locked holdout, or any season after the holdout."""
    allowed = matches["season"] <= HOLDOUT_SEASON if unlock_holdout else matches["season"] < HOLDOUT_SEASON
    if not allowed.all():
        blocked = sorted(matches.loc[~allowed, "season"].unique())
        raise HoldoutLockedError(
            f"seasons {blocked} are off limits (holdout {HOLDOUT_SEASON}, "
            f"{'unlocked' if unlock_holdout else 'locked'})"
        )


def evaluation_seasons(matches: pd.DataFrame, first_test_season: str) -> list[str]:
    """Seasons to test on, in order: `first_test_season` and every later season in `matches`."""
    return sorted(season for season in matches["season"].unique() if season >= first_test_season)


def walk_forward_splits(
    matches: pd.DataFrame,
    first_test_season: str = FIRST_TEST_SEASON,
    unlock_holdout: bool = False,
) -> Iterator[Fold]:
    """For each test season S, train on every match dated before S's first match."""
    check_holdout(matches, unlock_holdout)
    for season in evaluation_seasons(matches, first_test_season):
        test = matches[matches["season"] == season]
        train = matches[matches["date"] < test["date"].min()]
        yield Fold(season=season, train=train, test=test)
