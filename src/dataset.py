"""Model table: each evaluation match joined with its stored pre-match features.

Both files are read through splits.load_evaluation_matches, so the holdout is filtered
out at read time. The burn-in season is dropped from training and evaluation alike.
"""

from pathlib import Path

import pandas as pd

from src.config import FEATURES_PATH, MATCHES_PATH
from src.data import MATCH_COLUMNS
from src.splits import load_evaluation_matches

MATCH_KEY = ["date", "home", "away"]


def join_features(matches: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Matches with their features attached, one-to-one on date, home and away.

    Raises if any match has no feature row (features.parquet is stale).
    """
    added = features.drop(columns=[column for column in features.columns
                                   if column in MATCH_COLUMNS and column not in MATCH_KEY])
    table = matches.merge(added, on=MATCH_KEY, how="inner", validate="one_to_one")
    if len(table) != len(matches):
        raise ValueError(f"{len(matches) - len(table)} matches have no features; "
                         "run `python -m scripts.build_features`")
    return table


def model_feature_columns(table: pd.DataFrame) -> list[str]:
    """Model inputs: every column that isn't part of the match table or the burn-in flag,
    so goals, results, match stats and odds are never inputs."""
    return [column for column in table.columns if column not in MATCH_COLUMNS and column != "burn_in"]


def load_model_table(matches_path: Path = MATCHES_PATH, features_path: Path = FEATURES_PATH) -> pd.DataFrame:
    """Evaluation matches with features, burn-in rows removed."""
    table = join_features(load_evaluation_matches(matches_path), load_evaluation_matches(features_path))
    return table[~table["burn_in"]].reset_index(drop=True)
