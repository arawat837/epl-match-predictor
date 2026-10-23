"""Score the baselines and the three models walk-forward on the feature table.

Writes reports/model_metrics.csv (one row per predictor and season, plus averages),
reports/xgb_feature_importance.png and .csv. Burn-in rows are excluded; the holdout is
never read. Run from the project root: python -m scripts.evaluate_models
Exits with status 1 if the leakage tripwire fires.
"""

import sys

from src.baselines import BASELINES
from src.config import REPORTS_DIR
from src.dataset import load_model_table, model_feature_columns
from src.evaluate import format_alarms, format_table, save_table, walk_forward, with_average
from src.models import LogisticModel, XGBoostModel, elo_only, gain_importance
from src.plots import plot_importance
from src.splits import walk_forward_splits


def main() -> int:
    table = load_model_table()
    columns = model_feature_columns(table)
    xgboost = XGBoostModel(columns)
    predictors = {**BASELINES, "elo only": elo_only, "logistic (all)": LogisticModel(columns), "xgboost": xgboost}
    results = with_average(walk_forward(predictors, walk_forward_splits(table)))

    save_table(results, REPORTS_DIR / "model_metrics.csv")
    print(f"{len(table)} matches after dropping burn-in, {len(columns)} features\n")
    print(format_table(results))

    importance = gain_importance(list(xgboost.fitted.values()))
    importance.rename("gain_share").to_csv(REPORTS_DIR / "xgb_feature_importance.csv", index_label="feature")
    seasons = list(xgboost.fitted)
    plot_importance(importance, REPORTS_DIR / "xgb_feature_importance.png",
                    title="XGBoost feature importance (gain), top 15",
                    subtitle=f"Mean share of gain over {len(seasons)} walk-forward fits, "
                             f"test seasons {seasons[0]} to {seasons[-1]}")
    print(f"\nXGBoost trees chosen by early stopping: {xgboost.trees}")

    alarm = format_alarms(results)
    print(f"\n{alarm}" if alarm else "\nLeakage tripwire: not triggered")
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
