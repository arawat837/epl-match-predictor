"""Stage 10: the single holdout evaluation of the frozen final model.

Locked by default: every entry point requires unlock_holdout=True (the --unlock-holdout flag)
and a config byte-identical to the one committed under the pre-holdout-config tag. The
holdout is one more walk-forward fold: features and Elo use only earlier matches (Elo runs
match by match through the holdout), and the model, imputer and scaler are fitted once on
seasons up to 2024-25, with no refitting inside the holdout.
"""

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.baselines import base_rate, bookmaker
from src.config import HOLDOUT_SEASON, PROJECT_ROOT
from src.dataset import join_features
from src.evaluate import pre_match_view, score
from src.features import build_features
from src.final_model import CONFIG_PATH, elo_params, predictor
from src.metrics import OUTCOMES, log_losses
from src.models import elo_only
from src.splits import Fold, HoldoutLockedError, load_evaluation_matches, walk_forward_splits
from src.tuning import paired_difference, with_elo

TAG = "pre-holdout-config"
CONFIG_IN_REPO = "config/final_model.json"
HOLDOUT_MATCHES = 380


class ConfigChangedError(RuntimeError):
    """Raised when the config differs from the one frozen under the tag."""


def require_unlock(unlock_holdout: bool) -> None:
    """Refuse to touch the holdout unless explicitly unlocked."""
    if not unlock_holdout:
        raise HoldoutLockedError(f"the {HOLDOUT_SEASON} holdout is locked; pass --unlock-holdout to evaluate it")


def frozen_config_bytes(tag: str = TAG) -> bytes:
    """The config file as committed under the tag."""
    return subprocess.run(["git", "show", f"{tag}:{CONFIG_IN_REPO}"], cwd=PROJECT_ROOT,
                          capture_output=True, check=True).stdout


def check_config_frozen(path: Path = CONFIG_PATH, tag: str = TAG) -> None:
    """Abort unless the config file is byte-identical to the tagged one."""
    if path.read_bytes() != frozen_config_bytes(tag):
        raise ConfigChangedError(f"{path} differs from {tag}:{CONFIG_IN_REPO}; the holdout run is aborted")


def config_hash(path: Path = CONFIG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=PROJECT_ROOT, capture_output=True, check=True,
                          text=True).stdout.strip()


def git_commit() -> str:
    return git_output("rev-parse", "HEAD")


def working_tree_clean() -> bool:
    return git_output("status", "--porcelain") == ""


def holdout_matches(unlock_holdout: bool) -> pd.DataFrame:
    """Every match up to and including the holdout season (never anything after it)."""
    require_unlock(unlock_holdout)
    return load_evaluation_matches(unlock_holdout=True)


def check_holdout_size(matches: pd.DataFrame) -> pd.DataFrame:
    """The holdout season's matches; raises unless it is a complete 380-match season."""
    holdout = matches[matches["season"] == HOLDOUT_SEASON]
    if len(holdout) != HOLDOUT_MATCHES:
        raise ValueError(f"{HOLDOUT_SEASON} has {len(holdout)} matches, expected {HOLDOUT_MATCHES}")
    return holdout


def model_tables(matches: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(final-model table with the frozen Elo, table with the original Elo), burn-in dropped.
    Features are rebuilt over every match up to the holdout, each from earlier matches only."""
    table = join_features(matches, build_features(matches))
    table = table[~table["burn_in"]].reset_index(drop=True)
    return with_elo(table, matches, elo_params(config)), table


def holdout_fold(table: pd.DataFrame, unlock_holdout: bool) -> Fold:
    """The single walk-forward fold whose test season is the holdout."""
    folds = list(walk_forward_splits(table, HOLDOUT_SEASON, unlock_holdout=unlock_holdout))
    if [fold.season for fold in folds] != [HOLDOUT_SEASON]:
        raise ValueError(f"expected one holdout fold, got {[fold.season for fold in folds]}")
    return folds[0]


@dataclass(frozen=True)
class HoldoutRun:
    """Forecasts on the holdout matches from the final model and every comparison predictor."""

    fold: Fold
    forecasts: dict[str, pd.DataFrame]

    @property
    def results(self) -> pd.Series:
        return self.fold.test["result"]


def run_holdout(unlock_holdout: bool, config: dict) -> HoldoutRun:
    """Fit once on seasons up to the one before the holdout and forecast every holdout match."""
    require_unlock(unlock_holdout)
    check_config_frozen()
    matches = holdout_matches(unlock_holdout)
    check_holdout_size(matches)
    final_table, original_table = model_tables(matches, config)
    fold, original_fold = holdout_fold(final_table, unlock_holdout), holdout_fold(original_table, unlock_holdout)
    test = pre_match_view(fold.test)
    forecasts = {
        "final model": predictor(config)(fold.train, test),
        "bookmaker": bookmaker(fold.train, test),
        "base rate": base_rate(fold.train, test),
        "Elo-only (original, untuned)": elo_only(original_fold.train, pre_match_view(original_fold.test)),
    }
    return HoldoutRun(fold, forecasts)


def metrics_table(run: HoldoutRun) -> pd.DataFrame:
    """Log loss, RPS and accuracy on the holdout for every predictor."""
    return pd.DataFrame([{"predictor": name, "matches": len(probabilities), **score(probabilities, run.results)}
                         for name, probabilities in run.forecasts.items()])


def paired_table(run: HoldoutRun, against: list[str]) -> pd.DataFrame:
    """Final model's per-match log loss minus each reference's, with standard errors."""
    model = log_losses(run.forecasts["final model"], run.results)
    rows = []
    for name in against:
        difference, error = paired_difference(model, log_losses(run.forecasts[name], run.results))
        rows.append({"final model minus": name, "difference": difference, "standard_error": error,
                     "z": difference / error})
    return pd.DataFrame(rows)


def confusion_matrix(probabilities: pd.DataFrame, results: pd.Series) -> pd.DataFrame:
    """Counts of actual (rows) against predicted (columns) outcome."""
    predicted = probabilities[OUTCOMES].idxmax(axis=1)
    table = pd.crosstab(results.rename("actual"), predicted.rename("predicted"))
    return table.reindex(index=OUTCOMES, columns=OUTCOMES, fill_value=0)


def noise_check(run: HoldoutRun, reference: float) -> dict[str, float]:
    """Holdout log loss against the reporting-season average, in per-match standard errors."""
    losses = log_losses(run.forecasts["final model"], run.results)
    error = float(losses.std(ddof=1) / len(losses) ** 0.5)
    return {"holdout_log_loss": float(losses.mean()), "reporting_average": reference,
            "standard_error": error, "z": (float(losses.mean()) - reference) / error}
