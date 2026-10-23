"""Walk-forward evaluation harness: score predictors season by season and summarise.

A predictor is any function (train, test) -> H/D/A forecast for the test matches. It sees
the test season only through pre_match_view, so goals, result and match stats can't leak in.
"""

from collections.abc import Callable, Iterable, Mapping

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
LEAKAGE_ALARM_ACCURACY = 0.58
AVERAGE = "average"


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
    """Rows whose accuracy exceeds the leakage threshold (CLAUDE.md: stop and audit)."""
    return table[table["accuracy"] > LEAKAGE_ALARM_ACCURACY]


def metric_table(table: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Season-by-predictor table of one metric, keeping season and predictor order."""
    wide = table.pivot(index="season", columns="predictor", values=metric)
    return wide.loc[table["season"].unique(), table["predictor"].unique()]


def format_report(table: pd.DataFrame) -> str:
    """Text report: one season-by-predictor table per metric, then any leakage alarm."""
    sections = [f"{METRIC_TITLES[metric]}\n{metric_table(table, metric).to_string(float_format='{:.4f}'.format)}"
                for metric in METRICS]
    alarms = leakage_alarms(table)
    if not alarms.empty:
        sections.append(f"LEAKAGE ALARM: accuracy above {LEAKAGE_ALARM_ACCURACY:.0%}. "
                        f"Stop and audit before continuing.\n{alarms.to_string(index=False)}")
    return "\n\n".join(sections)
