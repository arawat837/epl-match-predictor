"""Stage 8 protocol: availability groups added to a frozen base, judged by a pre-registered rule.

Base: the frozen Stage 6 compact logistic (tuned Elo K=15, home_adv=50, carryover=0.9; C=0.03),
scored walk-forward from 2016-17 so every match from then on has an out-of-sample base
probability. The offset model trains on 2016-17 up to the season before each test season.
Lambda is chosen on the tuning seasons (2017-18 to 2019-20) only, then frozen; the reporting
seasons (2020-21 to 2024-25) are scored once. A group is adopted only if the cumulative
model beats base on the tuning seasons, on the reporting seasons pooled, and in at least 3
of the 5 reporting seasons.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import FIRST_REPORTING_SEASON
from src.dataset import MATCH_KEY
from src.elo import EloParams
from src.evaluate import Predictor, pooled, pre_match_view
from src.models import LogisticModel
from src.offset import BASE_COLUMNS, OffsetModel
from src.splits import Fold, walk_forward_splits
from src.tuning import COMPACT_FEATURES, paired_difference, run_folds

BASE_ELO = EloParams(K=15, home_adv=50, carryover=0.9)
BASE_C = 0.03
FIRST_BASE_SEASON = "2016-17"  # first season with FPL data: base probabilities from here on
FIRST_TUNING_SEASON = "2017-18"
LAMBDA_GRID = (0.001, 0.003, 0.01, 0.03, 0.1)
STEPS = [["suspension"], ["suspension", "squad_value"], ["suspension", "squad_value", "form"],
         ["suspension", "squad_value", "form", "recent_absence"]]
MIN_REPORTING_WINS = 3


def base_probabilities(table: pd.DataFrame) -> pd.DataFrame:
    """Frozen base model's walk-forward out-of-sample probabilities, seasons 2016-17 onward."""
    model = LogisticModel(COMPACT_FEATURES, C=BASE_C)
    forecasts = [model(fold.train, pre_match_view(fold.test)) for fold in walk_forward_splits(table, FIRST_BASE_SEASON)]
    return pd.concat(forecasts).set_axis(BASE_COLUMNS, axis=1)


def experiment_table(table: pd.DataFrame, base: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Matches from 2016-17 on with base probabilities and Stage 8 features attached."""
    with_base = table.join(base, how="inner")
    added = features.drop(columns=[column for column in features.columns if column in with_base.columns
                                   and column not in MATCH_KEY])
    merged = with_base.reset_index().merge(added, on=MATCH_KEY, how="left", validate="one_to_one")
    return merged.set_index("index").rename_axis(None)


def experiment_folds(table: pd.DataFrame) -> tuple[list[Fold], list[Fold]]:
    """(tuning folds, reporting folds); each trains on 2016-17 up to the season before."""
    folds = list(walk_forward_splits(table, FIRST_TUNING_SEASON))
    return ([fold for fold in folds if fold.season < FIRST_REPORTING_SEASON],
            [fold for fold in folds if fold.season >= FIRST_REPORTING_SEASON])


@dataclass(frozen=True)
class Window:
    """Per-season metrics and per-match log losses over one window of test seasons."""

    per_season: pd.DataFrame
    losses: pd.Series

    def pooled(self) -> pd.Series:
        return pooled(self.per_season).iloc[0]


@dataclass(frozen=True)
class Scored:
    name: str
    tuning: Window
    reporting: Window


def score(name: str, predictor: Predictor, tuning: list[Fold], reporting: list[Fold]) -> Scored:
    """A frozen predictor scored on the tuning seasons, then once on the reporting seasons."""
    return Scored(name, Window(*run_folds(name, predictor, tuning)), Window(*run_folds(name, predictor, reporting)))


def choose_lambda(columns: list[str], tuning: list[Fold]) -> pd.DataFrame:
    """Tuning-season log loss of the offset model for every lambda, best first."""
    rows = [{"lambda": lam, "tuning_log_loss": run_folds("offset", OffsetModel(columns, lam), tuning)[1].mean()}
            for lam in LAMBDA_GRID]
    return pd.DataFrame(rows).sort_values("tuning_log_loss", kind="stable", ignore_index=True)


def summary(scored: list[Scored]) -> pd.DataFrame:
    """Log loss, RPS and accuracy per model and window."""
    rows = []
    for result in scored:
        for window_name, window in (("tuning", result.tuning), ("reporting", result.reporting)):
            pooled_scores = window.pooled()
            rows.append({"model": result.name, "window": window_name, "matches": int(pooled_scores["matches"]),
                         "log_loss": pooled_scores["log_loss"], "rps": pooled_scores["rps"],
                         "accuracy": pooled_scores["accuracy"]})
    return pd.DataFrame(rows)


def versus(candidate: Scored, reference: Scored, seasons: pd.Series) -> pd.DataFrame:
    """Paired per-match log loss difference (candidate minus reference) per window and season."""
    rows = []
    for window_name in ("tuning", "reporting"):
        mine, theirs = getattr(candidate, window_name).losses, getattr(reference, window_name).losses
        difference, error = paired_difference(mine, theirs)
        rows.append({"window": window_name, "season": "pooled", "minus_base": difference, "standard_error": error})
        for season, index in mine.groupby(seasons.loc[mine.index]).groups.items():
            difference, error = paired_difference(mine.loc[index], theirs)
            rows.append({"window": window_name, "season": season, "minus_base": difference, "standard_error": error})
    return pd.DataFrame(rows)


def decision(candidate: Scored, base: Scored, seasons: pd.Series) -> dict[str, object]:
    """The pre-registered adoption rule, with each of its three parts."""
    differences = versus(candidate, base, seasons)
    pooled_rows = differences[differences["season"] == "pooled"].set_index("window")["minus_base"]
    reporting = differences[(differences["window"] == "reporting") & (differences["season"] != "pooled")]
    wins = int((reporting["minus_base"] < 0).sum())
    parts = {"beats_base_tuning": bool(pooled_rows["tuning"] < 0),
             "beats_base_reporting": bool(pooled_rows["reporting"] < 0),
             "reporting_seasons_won": f"{wins} of {len(reporting)}"}
    adopted = parts["beats_base_tuning"] and parts["beats_base_reporting"] and wins >= MIN_REPORTING_WINS
    return parts | {"decision": "adopted" if adopted else "not adopted"}
