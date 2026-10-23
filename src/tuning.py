"""Stage 6 tuning protocol: choose on tuning seasons, freeze, report once.

Tuning seasons (FIRST_TEST_SEASON up to FIRST_REPORTING_SEASON) pick every setting. The
choice is then frozen and scored once on the reporting seasons (FIRST_REPORTING_SEASON up
to the holdout). Every season's model still trains only on matches before it, and every
reporting season comes after all tuning seasons, so each reported model was tuned inside
its own training window. The holdout stays locked.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from src.config import FIRST_REPORTING_SEASON, FIRST_TEST_SEASON
from src.dataset import MATCH_KEY
from src.elo import EloParams, pre_match_elo
from src.evaluate import Predictor, pooled, pre_match_view, score, walk_forward
from src.metrics import log_losses
from src.models import XGB_PARAMS, LogisticModel, elo_only
from src.splits import Fold, walk_forward_splits

ELO_GRID = {"K": (10, 15, 20, 25, 30), "home_adv": (50, 65, 80, 95), "carryover": (0.6, 0.75, 0.9)}
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0)
COMPACT_FEATURES = ["elo_diff", "season_ppg_diff", "points_last10_diff", "gf_last10_diff",
                    "ga_last10_diff", "points_venue_last5_diff", "days_rest_diff"]
COMPACT_XGB_PARAMS = {**XGB_PARAMS, "max_depth": 2, "min_child_weight": 20, "learning_rate": 0.03}
ELO_COLUMNS = ["elo_home", "elo_away", "elo_diff"]
CLEAR_MARGIN_SE = 2  # a difference counts as clear beyond two standard errors


def tuning_folds(table: pd.DataFrame) -> list[Fold]:
    """Walk-forward folds whose test season is a tuning season."""
    return [fold for fold in walk_forward_splits(table, FIRST_TEST_SEASON) if fold.season < FIRST_REPORTING_SEASON]


def reporting_folds(table: pd.DataFrame) -> list[Fold]:
    """Walk-forward folds whose test season is a reporting season."""
    return list(walk_forward_splits(table, FIRST_REPORTING_SEASON))


def with_elo(table: pd.DataFrame, matches: pd.DataFrame, params: EloParams) -> pd.DataFrame:
    """The model table with its Elo columns recomputed under `params`. Ratings run over every
    evaluation match in `matches`, burn-in season included, as history."""
    elo = pd.concat([matches[MATCH_KEY], pre_match_elo(matches, params)], axis=1)
    rebuilt = table.drop(columns=ELO_COLUMNS).merge(elo, on=MATCH_KEY, how="left", validate="one_to_one")
    rebuilt.index = table.index
    return rebuilt[table.columns]


def pooled_log_loss(predictor: Predictor, folds: list[Fold]) -> float:
    """Log loss over all the folds' test matches."""
    return float(pooled(walk_forward({"model": predictor}, folds))["log_loss"].iloc[0])


def elo_candidates() -> list[EloParams]:
    """Every point of ELO_GRID."""
    return [EloParams(K=k, home_adv=home_adv, carryover=carryover)
            for k, home_adv, carryover in product(*ELO_GRID.values())]


def tune_elo(table: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Tuning-season log loss of Elo-only logistic regression at every Elo grid point, best first."""
    rows = [{"K": params.K, "home_adv": params.home_adv, "carryover": params.carryover,
             "tuning_log_loss": pooled_log_loss(elo_only, tuning_folds(with_elo(table, matches, params)))}
            for params in elo_candidates()]
    return pd.DataFrame(rows).sort_values("tuning_log_loss", kind="stable", ignore_index=True)


def best_elo(grid: pd.DataFrame) -> EloParams:
    """Elo parameters of the best grid row."""
    best = grid.iloc[0]
    return EloParams(K=float(best["K"]), home_adv=float(best["home_adv"]), carryover=float(best["carryover"]))


def tune_c(table: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Tuning-season log loss of L2 logistic regression on `columns` for every C, best first."""
    folds = tuning_folds(table)
    rows = [{"C": c, "tuning_log_loss": pooled_log_loss(LogisticModel(columns, C=c), folds)} for c in C_GRID]
    return pd.DataFrame(rows).sort_values("tuning_log_loss", kind="stable", ignore_index=True)


@dataclass(frozen=True)
class Result:
    """A frozen model scored on the tuning seasons and then once on the reporting seasons."""

    name: str
    tuning: pd.DataFrame  # per-season metrics
    reporting: pd.DataFrame  # per-season metrics
    reporting_losses: pd.Series  # per-match log loss on the reporting seasons

    @property
    def tuning_log_loss(self) -> float:
        return float(pooled(self.tuning)["log_loss"].iloc[0])

    @property
    def reporting_log_loss(self) -> float:
        return float(pooled(self.reporting)["log_loss"].iloc[0])


def run_folds(name: str, predictor: Predictor, folds: list[Fold]) -> tuple[pd.DataFrame, pd.Series]:
    """Per-season metrics and per-match log losses for one predictor over `folds`."""
    rows, losses = [], []
    for fold in folds:
        probabilities = predictor(fold.train, pre_match_view(fold.test))
        rows.append({"predictor": name, "season": fold.season, "matches": len(fold.test),
                     **score(probabilities, fold.test["result"])})
        losses.append(log_losses(probabilities, fold.test["result"]))
    return pd.DataFrame(rows), pd.concat(losses)


def evaluate_frozen(name: str, predictor: Predictor, table: pd.DataFrame) -> Result:
    """Score a frozen model on the tuning seasons, then once on the reporting seasons."""
    tuning, _ = run_folds(name, predictor, tuning_folds(table))
    reporting, losses = run_folds(name, predictor, reporting_folds(table))
    return Result(name, tuning, reporting, losses)


def previous_best(results: list[Result]) -> Result:
    """The model with the lowest tuning-season log loss so far."""
    return min(results, key=lambda result: result.tuning_log_loss)


def step_table(bookmaker: Result, original: Result, best_so_far: Result, new: Result) -> pd.DataFrame:
    """Tuning and reporting log loss of a step's frozen model next to the references."""
    rows = [("bookmaker", bookmaker), ("original Elo-only", original),
            (f"previous best: {best_so_far.name}", best_so_far), (f"this step: {new.name}", new)]
    return pd.DataFrame([{"model": label, "tuning_log_loss": result.tuning_log_loss,
                          "reporting_log_loss": result.reporting_log_loss} for label, result in rows])


def paired_difference(candidate: pd.Series, reference: pd.Series) -> tuple[float, float]:
    """Mean per-match log loss difference (candidate minus reference) and its standard error."""
    difference = candidate - reference.loc[candidate.index]
    return float(difference.mean()), float(difference.std(ddof=1) / np.sqrt(len(difference)))


def verdict(difference: float, standard_error: float) -> str:
    """Plain-language reading of a reporting-season log loss difference."""
    if difference >= 0:
        return "does not beat"
    clear = -difference > CLEAR_MARGIN_SE * standard_error
    return "beats, clearly" if clear else "beats, within noise"


def versus_original(results: list[Result], original: Result) -> pd.DataFrame:
    """Reporting-season log loss of each model against the original Elo-only model."""
    rows = []
    for result in results:
        difference, standard_error = paired_difference(result.reporting_losses, original.reporting_losses)
        rows.append({"model": result.name, "reporting_log_loss": result.reporting_log_loss,
                     "minus_original": difference, "standard_error": standard_error,
                     "verdict": verdict(difference, standard_error)})
    return pd.DataFrame(rows)
