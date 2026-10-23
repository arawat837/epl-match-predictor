"""Stage 6: tune on 2015-16 to 2019-20, freeze, report once on 2020-21 to 2024-25.

A) Elo grid for Elo-only logistic regression. B) Compact L2 logistic regression, C tuned.
C) Compact XGBoost (depth 2, min_child_weight 20, learning rate 0.03). Steps B and C use the
Elo parameters frozen in step A. The holdout is never read.
Run from the project root: python -m scripts.tune_models
Writes reports/stage6_*.csv. Exits with status 1 if the leakage tripwire fires.
"""

import sys

import pandas as pd

from src.baselines import BASELINES
from src.config import REPORTS_DIR
from src.dataset import load_model_table, model_feature_columns
from src.evaluate import format_alarms, save_table
from src.models import LogisticModel, XGBoostModel, elo_only
from src.splits import load_evaluation_matches
from src.tuning import (
    COMPACT_FEATURES,
    COMPACT_XGB_PARAMS,
    best_elo,
    evaluate_frozen,
    previous_best,
    step_table,
    tune_c,
    tune_elo,
    versus_original,
    with_elo,
)

FLOAT = "{:.4f}".format


def show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n{title}\n{frame.to_string(index=False, float_format=FLOAT)}")


def main() -> int:
    matches = load_evaluation_matches()
    table = load_model_table()
    columns = model_feature_columns(table)
    bookmaker = evaluate_frozen("bookmaker", BASELINES["bookmaker"], table)
    original = evaluate_frozen("elo only (original)", elo_only, table)
    results = [original,
               evaluate_frozen("logistic (all), stage 5", LogisticModel(columns), table),
               evaluate_frozen("xgboost (all), stage 5", XGBoostModel(columns), table)]

    grid = tune_elo(table, matches)
    grid.to_csv(REPORTS_DIR / "stage6_elo_grid.csv", index=False)
    show("A) Elo grid, tuning-season log loss (best 5 of 60)", grid.head(5))
    elo = best_elo(grid)
    tuned = with_elo(table, matches, elo)
    step_a = evaluate_frozen(f"elo only, tuned Elo (K={elo.K:g}, home_adv={elo.home_adv:g}, "
                             f"carryover={elo.carryover:g})", elo_only, tuned)
    show("A) frozen and reported", step_table(bookmaker, original, previous_best(results), step_a))
    results.append(step_a)

    c_grid = tune_c(tuned, COMPACT_FEATURES)
    c_grid.to_csv(REPORTS_DIR / "stage6_c_grid.csv", index=False)
    show("B) C grid, tuning-season log loss", c_grid)
    best_c = float(c_grid.iloc[0]["C"])
    step_b = evaluate_frozen(f"compact logistic (C={best_c:g})", LogisticModel(COMPACT_FEATURES, C=best_c), tuned)
    show("B) frozen and reported", step_table(bookmaker, original, previous_best(results), step_b))
    results.append(step_b)

    xgboost = XGBoostModel(COMPACT_FEATURES, params=COMPACT_XGB_PARAMS)
    step_c = evaluate_frozen("compact xgboost (depth 2, mcw 20, lr 0.03)", xgboost, tuned)
    show("C) frozen and reported", step_table(bookmaker, original, previous_best(results), step_c))
    print(f"   trees chosen by early stopping: {xgboost.trees}")
    results.append(step_c)

    comparison = versus_original(results[1:], original)
    comparison.to_csv(REPORTS_DIR / "stage6_vs_original.csv", index=False)
    show("Reporting seasons 2020-21 to 2024-25 against the original Elo-only "
         f"(original {original.reporting_log_loss:.4f}, bookmaker {bookmaker.reporting_log_loss:.4f})", comparison)

    per_season = pd.concat([frame for result in [bookmaker, *results] for frame in (result.tuning, result.reporting)],
                           ignore_index=True)
    save_table(per_season, REPORTS_DIR / "stage6_per_season.csv")
    alarm = format_alarms(per_season)
    print(f"\n{alarm}" if alarm else "\nLeakage tripwire: not triggered")
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
