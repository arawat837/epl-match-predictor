"""Stage 9: calibration test, reliability and confidence analysis of the frozen final model.

Out-of-sample walk-forward forecasts come from config/final_model.json, from 2015-16 so that
2016-17's temperature can be fitted on 2015-16. Analysis covers 2016-17 to 2024-25; the
holdout is never read. Writes reports/stage9_*.csv and reports/stage9_reliability.png.
Run from the project root: python -m scripts.analyse_final_model
"""

import sys

import pandas as pd

from src.calibration import calibrate_walk_forward
from src.config import FIRST_REPORTING_SEASON, REPORTS_DIR
from src.confidence import calibration_gap, overlap_table, per_season_table, reliability_table, subset_table
from src.evaluate import format_alarms, score
from src.final_model import load_config, model_table, out_of_sample
from src.metrics import OUTCOMES
from src.odds import implied_probabilities
from src.plots import plot_reliability

FIRST_SEASON = "2016-17"
FLOAT = "{:.4f}".format


def show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n{title}\n{frame.to_string(index=False, float_format=FLOAT)}")


def window_scores(name: str, forecasts: pd.DataFrame) -> list[dict[str, object]]:
    """Pooled log loss, RPS and accuracy on the tuning and reporting seasons."""
    rows = []
    for window, mask in (("tuning 2016-17..2019-20", forecasts["season"] < FIRST_REPORTING_SEASON),
                         ("reporting 2020-21..2024-25", forecasts["season"] >= FIRST_REPORTING_SEASON)):
        part = forecasts[mask]
        rows.append({"forecast": name, "window": window, "matches": len(part),
                     **score(part[OUTCOMES], part["result"])})
    return rows


def per_season_rows(name: str, forecasts: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"predictor": name, "season": season, "matches": len(part),
                          **score(part[OUTCOMES], part["result"])} for season, part in forecasts.groupby("season")])


def main() -> int:
    config = load_config()
    table = model_table(config)
    raw_all = out_of_sample(config, table, "2015-16")
    calibrated, temperatures = calibrate_walk_forward(raw_all, FIRST_SEASON)
    raw = raw_all.loc[calibrated.index]
    comparison = pd.DataFrame(window_scores("raw", raw) + window_scores("temperature-scaled", calibrated))
    comparison.to_csv(REPORTS_DIR / "stage9_calibration.csv", index=False)
    show("Temperature per test season (fitted on the season before)", temperatures.rename_axis("season").reset_index())
    show("Calibration test", comparison)
    tuning = comparison[comparison["window"].str.startswith("tuning")].set_index("forecast")["log_loss"]
    keep = tuning["temperature-scaled"] < tuning["raw"]
    print(f"\nTemperature scaling {'KEPT' if keep else 'NOT kept'}: tuning log loss "
          f"{tuning['raw']:.4f} raw vs {tuning['temperature-scaled']:.4f} scaled")

    model = calibrated if keep else raw
    results, seasons = model["result"], model["season"]
    bookmaker = implied_probabilities(table.loc[model.index])
    reliability = reliability_table(model, results)
    reliability.to_csv(REPORTS_DIR / "stage9_reliability.csv", index=False)
    show("Reliability (deciles of predicted probability, pooled 2016-17..2024-25)", reliability)
    show("Mean absolute calibration gap per outcome", calibration_gap(reliability).rename("gap").reset_index())
    plot_reliability(reliability, REPORTS_DIR / "stage9_reliability.png",
                     title="Final model reliability, 2016-17 to 2024-25",
                     subtitle=f"{len(model)} out-of-sample matches; each point is a decile of about "
                              f"{len(model) // 10} matches; diagonal = perfect calibration")

    predictors = {"final model": model[OUTCOMES], "bookmaker": bookmaker}
    subsets = subset_table(predictors, results)
    subsets.to_csv(REPORTS_DIR / "stage9_confidence.csv", index=False)
    show("Confidence subsets, pooled 2016-17..2024-25 (reliable = at least 100 matches)", subsets)
    overlap = overlap_table(model[OUTCOMES], bookmaker)
    overlap.to_csv(REPORTS_DIR / "stage9_overlap.csv", index=False)
    show("Model's most confident matches that are also the bookmaker's", overlap)
    by_season = per_season_table(predictors, results, seasons)
    by_season.to_csv(REPORTS_DIR / "stage9_confidence_by_season.csv", index=False)
    counts = by_season.pivot_table(index=["predictor", "subset"], columns="season", values="matches", fill_value=0)
    print(f"\nMatches per season in each subset (cells under 100 are unreliable)\n{counts.to_string()}")

    per_season = pd.concat([per_season_rows("final model", model),
                            per_season_rows("bookmaker", bookmaker.join(model[["season", "result"]]))])
    alarm = format_alarms(per_season)
    print(f"\n{alarm}" if alarm else "\nLeakage tripwire: not triggered")
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
