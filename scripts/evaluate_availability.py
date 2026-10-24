"""Stage 8: availability and form features on top of the frozen Stage 6 base, judged honestly.

Gating check, Stage 8 feature build (data/processed/availability_features.parquet), base
out-of-sample probabilities from 2016-17, four cumulative offset-model steps with lambda
chosen on the tuning seasons, the pre-registered decision rule, robustness check B, and the
leakage tripwire. The holdout is never read.
Run from the project root: python -m scripts.evaluate_availability
Exits with status 1 if the gating check fails or the tripwire fires.
"""

import sys

import pandas as pd

from src.audit import squad_listing_check
from src.availability_features import build_availability_features, group_columns
from src.baselines import bookmaker
from src.config import PROCESSED_DIR, REPORTS_DIR
from src.dataset import load_model_table
from src.evaluate import format_alarms, save_table
from src.experiments import (BASE_C, BASE_ELO, STEPS, base_probabilities, choose_lambda, decision,
                             experiment_folds, experiment_table, score, summary, versus)
from src.fpl import load_fpl
from src.models import LogisticModel
from src.name_maps import link_rows, load_overrides, team_name_map
from src.offset import OffsetModel, base_forecast
from src.splits import load_evaluation_matches
from src.tuning import COMPACT_FEATURES, with_elo

FEATURES_PATH = PROCESSED_DIR / "availability_features.parquet"
MIN_ZERO_MINUTE_SHARE = 0.05  # a listing with almost no 0-minute players lists only who played
FLOAT = "{:.4f}".format


def show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n{title}\n{frame.to_string(index=False, float_format=FLOAT)}")


def main() -> int:
    matches = load_evaluation_matches()
    rows = load_fpl()
    names = team_name_map(list(rows["fpl_team"].unique()), load_overrides())
    linked = link_rows(rows, matches, dict(zip(names["fpl_name"], names["canonical"])))

    listing = squad_listing_check(linked)
    listing.to_csv(REPORTS_DIR / "stage8_squad_listing.csv")
    show("Gating check: FPL squad listing per team per match", listing.reset_index())
    if (listing["zero_minute_share"] < MIN_ZERO_MINUTE_SHARE).any():
        print("GATING CHECK FAILED: a season lists only players who played; stop.")
        return 1

    fpl_matches = matches[matches["season"] >= rows["season"].min()]
    features = build_availability_features(linked, fpl_matches)
    features.to_parquet(FEATURES_PATH)
    table = with_elo(load_model_table(), matches, BASE_ELO)
    data = experiment_table(table, base_probabilities(table), features)
    seasons = data["season"]
    tuning, reporting = experiment_folds(data)
    print(f"\n{len(data)} matches from 2016-17; tuning {[f.season for f in tuning]}, reporting {[f.season for f in reporting]}")

    market = score("bookmaker", bookmaker, tuning, reporting)
    base = score(f"base (compact logistic C={BASE_C:g}, tuned Elo)", base_forecast, tuning, reporting)
    everything, decisions, step_tables = [market, base], [], []
    for step, groups in enumerate(STEPS, start=1):
        columns = group_columns(groups)
        grid = choose_lambda(columns, tuning)
        lam = float(grid.iloc[0]["lambda"])
        model = score(f"base + {' + '.join(groups)} (lambda={lam:g})", OffsetModel(columns, lam), tuning, reporting)
        everything.append(model)
        show(f"Step {step}: lambda grid, tuning-season log loss", grid)
        show(f"Step {step}: identical matches", summary([base, model, market]))
        differences = versus(model, base, seasons)
        show(f"Step {step}: paired log loss difference vs base (negative = better)", differences)
        verdict = {"step": step, "groups": " + ".join(groups), "lambda": lam} | decision(model, base, seasons)
        print(f"Step {step} decision for group '{groups[-1]}': {verdict['decision']}  {verdict}")
        decisions.append(verdict)
        step_tables.append(differences.assign(step=step))

    new_columns = group_columns(STEPS[-1])
    without = score("robustness B: compact logistic, 2016-17 on, without", LogisticModel(COMPACT_FEATURES, C=BASE_C),
                    tuning, reporting)
    with_new = score("robustness B: compact logistic, 2016-17 on, with all groups",
                     LogisticModel(COMPACT_FEATURES + new_columns, C=BASE_C), tuning, reporting)
    everything += [without, with_new]
    show("Robustness B (identical training windows from 2016-17)", summary([without, with_new, market]))
    show("Robustness B: with minus without, paired", versus(with_new, without, seasons).rename(
        columns={"minus_base": "with_minus_without"}))

    pd.DataFrame(decisions).to_csv(REPORTS_DIR / "stage8_decisions.csv", index=False)
    pd.concat(step_tables).to_csv(REPORTS_DIR / "stage8_differences.csv", index=False)
    summary(everything).to_csv(REPORTS_DIR / "stage8_summary.csv", index=False)
    per_season = pd.concat([frame for result in everything for frame in (result.tuning.per_season,
                                                                         result.reporting.per_season)])
    save_table(per_season, REPORTS_DIR / "stage8_per_season.csv")
    show("Decisions (pre-registered rule)", pd.DataFrame(decisions))

    alarm = format_alarms(per_season)
    print(f"\n{alarm}" if alarm else "\nLeakage tripwire: not triggered")
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
