"""The frozen final model recorded in config/final_model.json: load it and build its predictor."""

import json
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT
from src.dataset import load_model_table
from src.elo import EloParams
from src.evaluate import pre_match_view
from src.models import LogisticModel
from src.splits import load_evaluation_matches, walk_forward_splits
from src.tuning import with_elo

CONFIG_PATH = PROJECT_ROOT / "config" / "final_model.json"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """The frozen configuration."""
    return json.loads(path.read_text(encoding="utf-8"))


def elo_params(config: dict) -> EloParams:
    return EloParams(**config["elo"])


def predictor(config: dict) -> LogisticModel:
    """The final model: L2 logistic regression on the frozen features, imputer and scaler per window."""
    return LogisticModel(config["features"], C=config["model"]["C"])


def model_table(config: dict) -> pd.DataFrame:
    """Evaluation matches with features, burn-in dropped, Elo recomputed under the frozen settings."""
    return with_elo(load_model_table(), load_evaluation_matches(), elo_params(config))


def out_of_sample(config: dict, table: pd.DataFrame, first_season: str) -> pd.DataFrame:
    """Walk-forward H/D/A forecasts from `first_season` on, each from a model trained on earlier
    seasons only, with each match's season and result attached."""
    model = predictor(config)
    forecasts = [model(fold.train, pre_match_view(fold.test)) for fold in walk_forward_splits(table, first_season)]
    forecasts = pd.concat(forecasts)
    return forecasts.join(table[["season", "result"]])
