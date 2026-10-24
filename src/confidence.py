"""Reliability and confidence analysis of pooled out-of-sample forecasts.

Confidence is a forecast's top probability. Subsets are by threshold (top probability above
0.45 ... 0.65) or by coverage (each predictor's own most confident 10/20/30% of matches,
ties kept in match order). Any cell with fewer than 100 matches is marked unreliable.
"""

import numpy as np
import pandas as pd

from src.metrics import OUTCOMES

THRESHOLDS = (0.45, 0.50, 0.55, 0.60, 0.65)
COVERAGES = (0.10, 0.20, 0.30)
MIN_RELIABLE = 100
RELIABILITY_BINS = 10


def top_probability(probabilities: pd.DataFrame) -> pd.Series:
    return probabilities[OUTCOMES].max(axis=1)


def is_correct(probabilities: pd.DataFrame, results: pd.Series) -> pd.Series:
    """Whether the most probable outcome happened (ties go to the first in H, D, A)."""
    return probabilities[OUTCOMES].idxmax(axis=1) == results.loc[probabilities.index]


def cell(correct: pd.Series) -> dict[str, object]:
    """Match count, accuracy and reliability flag for one subset."""
    return {"matches": len(correct), "accuracy": float(correct.mean()) if len(correct) else float("nan"),
            "reliable": len(correct) >= MIN_RELIABLE}


def most_confident(probabilities: pd.DataFrame, coverage: float) -> pd.Index:
    """Index of the predictor's own most confident `coverage` share of matches."""
    count = int(round(coverage * len(probabilities)))
    return top_probability(probabilities).sort_values(ascending=False, kind="stable").index[:count]


def subsets(probabilities: pd.DataFrame) -> dict[str, pd.Index]:
    """Every threshold and coverage subset of one predictor's matches."""
    top = top_probability(probabilities)
    named = {f"top probability > {threshold:.2f}": top.index[top > threshold] for threshold in THRESHOLDS}
    return named | {f"most confident {coverage:.0%}": most_confident(probabilities, coverage) for coverage in COVERAGES}


def subset_table(predictors: dict[str, pd.DataFrame], results: pd.Series) -> pd.DataFrame:
    """Matches and accuracy per predictor and subset, pooled."""
    rows = []
    for name, probabilities in predictors.items():
        correct = is_correct(probabilities, results)
        for subset, index in subsets(probabilities).items():
            rows.append({"predictor": name, "subset": subset,
                         "lowest_top_probability": float(top_probability(probabilities).loc[index].min()),
                         **cell(correct.loc[index])})
    return pd.DataFrame(rows)


def overlap_table(model: pd.DataFrame, bookmaker: pd.DataFrame) -> pd.DataFrame:
    """Share of the model's most confident matches that are also the bookmaker's, per coverage."""
    rows = []
    for coverage in COVERAGES:
        mine, theirs = most_confident(model, coverage), most_confident(bookmaker, coverage)
        rows.append({"coverage": f"{coverage:.0%}", "matches": len(mine),
                     "also_bookmaker_most_confident": len(mine.intersection(theirs)) / len(mine)})
    return pd.DataFrame(rows)


def per_season_table(predictors: dict[str, pd.DataFrame], results: pd.Series, seasons: pd.Series) -> pd.DataFrame:
    """Matches and accuracy per predictor, subset and season (subsets chosen on the pooled data)."""
    rows = []
    for name, probabilities in predictors.items():
        correct = is_correct(probabilities, results)
        for subset, index in subsets(probabilities).items():
            for season, season_index in correct.loc[index].groupby(seasons.loc[index]).groups.items():
                rows.append({"predictor": name, "subset": subset, "season": season,
                             **cell(correct.loc[season_index])})
    return pd.DataFrame(rows)


def reliability_table(probabilities: pd.DataFrame, results: pd.Series) -> pd.DataFrame:
    """Per outcome, predicted probabilities in decile bins: mean predicted, observed frequency, count."""
    rows = []
    for outcome in OUTCOMES:
        predicted = probabilities[outcome]
        happened = (results.loc[predicted.index] == outcome).astype(float)
        bins = pd.qcut(predicted, RELIABILITY_BINS, labels=False, duplicates="drop")
        for decile, members in predicted.groupby(bins).groups.items():
            rows.append({"outcome": outcome, "decile": int(decile) + 1,
                         "lower": float(predicted.loc[members].min()), "upper": float(predicted.loc[members].max()),
                         "predicted": float(predicted.loc[members].mean()),
                         "observed": float(happened.loc[members].mean()),
                         "matches": len(members), "reliable": len(members) >= MIN_RELIABLE})
    return pd.DataFrame(rows)


def calibration_gap(table: pd.DataFrame) -> pd.Series:
    """Match-weighted mean absolute gap between predicted and observed, per outcome."""
    gap = (table["predicted"] - table["observed"]).abs() * table["matches"]
    return gap.groupby(table["outcome"]).sum() / table.groupby("outcome")["matches"].sum()
