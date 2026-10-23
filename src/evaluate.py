"""Walk-forward evaluation harness: score predictors season by season and summarise.

A predictor is any function (train, test) -> H/D/A forecast for the test matches. It sees
the test season only through pre_match_view, so goals, result and match stats can't leak in.
"""

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import POST_MATCH_COLUMNS
from src.metrics import accuracy, log_loss, ranked_probability_score
from src.splits import Fold

Predictor = Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]

# Reporting order: proper scoring rules first, accuracy second.
METRICS = {"log_loss": log_loss, "rps": ranked_probability_score, "accuracy": accuracy}
METRIC_TITLES = {
    "log_loss": "Log loss (lower is better)",
    "rps": "Ranked probability score (lower is better)",
    "accuracy": "Accuracy (higher is better)",
}
TRIPWIRE_POOLED_ACCURACY = 0.58
BOOKMAKER = "bookmaker"
AVERAGE = "average"
NOT_AVAILABLE = "n/a"


def pre_match_view(matches: pd.DataFrame) -> pd.DataFrame:
    """What a predictor may know about the matches it forecasts: no post-match columns."""
    return matches.drop(columns=POST_MATCH_COLUMNS)


def score(probabilities: pd.DataFrame, outcomes: pd.Series) -> dict[str, float]:
    """Every metric for one set of forecasts."""
    return {name: metric(probabilities, outcomes) for name, metric in METRICS.items()}


def evaluate_fold(name: str, predictor: Predictor, fold: Fold) -> dict[str, str | int | float]:
    """Fit-and-forecast one predictor on one fold and score it."""
    probabilities = predictor(fold.train, pre_match_view(fold.test))
    return {"predictor": name, "season": fold.season, "matches": len(fold.test),
            **score(probabilities, fold.test["result"])}


def walk_forward(predictors: Mapping[str, Predictor], folds: Iterable[Fold]) -> pd.DataFrame:
    """Per-season metrics, one row per (predictor, season)."""
    rows = [evaluate_fold(name, predictor, fold)
            for fold in folds for name, predictor in predictors.items()]
    return pd.DataFrame(rows)


def pooled(table: pd.DataFrame) -> pd.DataFrame:
    """One AVERAGE row per predictor: the match-weighted mean over seasons, which equals
    each metric computed over all walk-forward matches at once."""
    by_predictor = table.groupby("predictor", sort=False)
    matches = by_predictor["matches"].sum()
    weighted = table[list(METRICS)].mul(table["matches"], axis=0).groupby(table["predictor"], sort=False).sum()
    averages = weighted.div(matches, axis=0).assign(matches=matches, season=AVERAGE)
    return averages.reset_index()[table.columns]


def with_average(table: pd.DataFrame) -> pd.DataFrame:
    """Per-season rows followed by each predictor's average row."""
    return pd.concat([table, pooled(table)], ignore_index=True)


def leakage_alarms(table: pd.DataFrame) -> pd.DataFrame:
    """Leakage tripwire (CLAUDE.md): pooled rows where accuracy exceeds 58%, or where a
    predictor's log loss beats the bookmaker's. Single seasons above 58% don't count."""
    scores = pooled(table[table["season"] != AVERAGE])
    too_accurate = scores["accuracy"] > TRIPWIRE_POOLED_ACCURACY
    beats_bookmaker = pd.Series(False, index=scores.index)
    if BOOKMAKER in set(scores["predictor"]):
        bookmaker_log_loss = scores.loc[scores["predictor"] == BOOKMAKER, "log_loss"].iloc[0]
        beats_bookmaker = (scores["predictor"] != BOOKMAKER) & (scores["log_loss"] < bookmaker_log_loss)
    reasons = [", ".join(reason for reason, hit in [
        (f"pooled accuracy above {TRIPWIRE_POOLED_ACCURACY:.0%}", accurate),
        ("pooled log loss beats the bookmaker", beats)] if hit)
        for accurate, beats in zip(too_accurate, beats_bookmaker)]
    return scores.assign(reason=reasons)[too_accurate | beats_bookmaker]


def reportable(table: pd.DataFrame) -> pd.DataFrame:
    """Log loss of a 0/1 forecast (always home) is infinite; report it as missing (n/a)."""
    return table.assign(log_loss=table["log_loss"].replace(np.inf, np.nan))


def save_table(table: pd.DataFrame, path: Path) -> Path:
    """Write the metrics table to CSV with n/a for undefined log loss."""
    path.parent.mkdir(parents=True, exist_ok=True)
    reportable(table).to_csv(path, index=False, na_rep=NOT_AVAILABLE)
    return path


def metric_table(table: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Season-by-predictor table of one metric, keeping season and predictor order."""
    wide = table.pivot(index="season", columns="predictor", values=metric)
    return wide.loc[table["season"].unique(), table["predictor"].unique()]


def format_table(table: pd.DataFrame) -> str:
    """One table, a row per (season, predictor): each season's predictors side by side,
    the average block last, metrics in reporting order."""
    in_order = reportable(table).assign(
        season=pd.Categorical(table["season"], categories=table["season"].unique(), ordered=True),
        predictor=pd.Categorical(table["predictor"], categories=table["predictor"].unique(), ordered=True),
    ).sort_values(["season", "predictor"])
    columns = ["season", "predictor", "matches", *METRICS]
    return in_order[columns].to_string(index=False, float_format="{:.4f}".format, na_rep=NOT_AVAILABLE)


def format_alarms(table: pd.DataFrame) -> str | None:
    """The tripwire message, or None if it didn't fire."""
    alarms = leakage_alarms(table)
    if alarms.empty:
        return None
    rows = reportable(alarms).to_string(index=False, float_format="{:.4f}".format, na_rep=NOT_AVAILABLE)
    return f"LEAKAGE TRIPWIRE: stop and audit before continuing.\n{rows}"


def format_report(table: pd.DataFrame) -> str:
    """Text report: one season-by-predictor table per metric, then the tripwire if it fired."""
    readable = reportable(table)
    sections = [f"{METRIC_TITLES[metric]}\n"
                f"{metric_table(readable, metric).to_string(float_format='{:.4f}'.format, na_rep=NOT_AVAILABLE)}"
                for metric in METRICS]
    alarm = format_alarms(table)
    return "\n\n".join([*sections, alarm] if alarm else sections)
