"""Stage 10: evaluate the frozen final model ONCE on the 2025-26 holdout.

Run from the project root: python -m scripts.evaluate_holdout --unlock-holdout
Refuses without --unlock-holdout, aborts if config/final_model.json differs from the
pre-holdout-config tag, and refuses a second run unless --rerun-reason explains it (a genuine
bug fix). Writes reports/stage10_holdout.csv, stage10_confidence.csv, stage10_predictions.csv,
stage10_holdout.md and appends to reports/stage10_run_log.json.
Exits with status 1 if the tripwire fires (model log loss beats the bookmaker's).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import HOLDOUT_SEASON, REPORTS_DIR
from src.confidence import subset_table
from src.final_model import load_config
from src.holdout import (TAG, check_config_frozen, config_hash, confusion_matrix, git_commit, metrics_table,
                         noise_check, paired_table, require_unlock, run_holdout, working_tree_clean)
from src.metrics import OUTCOMES

RUN_LOG = REPORTS_DIR / "stage10_run_log.json"
REPORTING_AVERAGE = 0.9818  # frozen model, reporting seasons 2020-21..2024-25 (Stage 6)
BASELINES = ["bookmaker", "Elo-only (original, untuned)"]


def parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--unlock-holdout", action="store_true", help="required: evaluate the locked holdout")
    parser.add_argument("--rerun-reason", default=None, help="required for any run after the first")
    return parser.parse_args(argv)


def previous_runs(path: Path = RUN_LOG) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def check_rerun(runs: list[dict], reason: str | None) -> None:
    """The holdout is evaluated once; any later run must say why."""
    if runs and not reason:
        raise RuntimeError(f"the holdout was already evaluated {len(runs)} time(s); a rerun needs --rerun-reason")


def append_run(entry: dict, path: Path = RUN_LOG) -> None:
    path.write_text(json.dumps([*previous_runs(path), entry], indent=2), encoding="utf-8")


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    """A GitHub markdown table (floats rounded)."""
    def text(value: object) -> str:
        return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
    header = "| " + " | ".join(str(column) for column in frame.columns) + " |"
    rule = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = ["| " + " | ".join(text(value) for value in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def report(entry: dict, metrics: pd.DataFrame, paired: pd.DataFrame, confusion: pd.DataFrame,
           confidence: pd.DataFrame, noise: dict) -> str:
    within = abs(noise["z"]) < 2
    return "\n\n".join([
        f"# Stage 10: holdout evaluation ({HOLDOUT_SEASON})",
        f"Run {entry['timestamp']} at commit `{entry['git_commit']}` (working tree clean: "
        f"{entry['working_tree_clean']}); config sha256 `{entry['config_sha256']}`, identical to `{TAG}`. "
        f"{entry['holdout_matches']} matches, last match {entry['last_match_date']}. "
        "Model fitted once on seasons up to 2024-25; no refitting inside the holdout.",
        "## Holdout metrics\n\n" + markdown_table(metrics),
        "## Paired per-match log loss difference (final model minus reference; negative = model better)\n\n"
        + markdown_table(paired),
        "## Confusion matrix (final model; rows actual, columns predicted)\n\n"
        + markdown_table(confusion.reset_index().rename(columns={"actual": "actual \\ predicted"}), digits=0),
        "## Confidence (Stage 9 definitions; reliable = at least 100 matches)\n\n" + markdown_table(confidence)
        + "\n\nThe top-10% (38 matches) and top-20% (76 matches) cells are too small to quote alone.",
        "## Noise\n\n"
        f"Holdout log loss {noise['holdout_log_loss']:.4f} against the {noise['reporting_average']:.4f} "
        f"reporting-season average: a difference of {noise['holdout_log_loss'] - noise['reporting_average']:+.4f}, "
        f"{noise['z']:+.2f} per-match standard errors (SE {noise['standard_error']:.4f} over 380 matches). "
        + ("That is within the noise expected from one 380-match season." if within
           else "That is outside two standard errors of the reporting average."),
    ]) + "\n"


def main(argv: list[str] | None = None) -> int:
    arguments = parse(argv)
    require_unlock(arguments.unlock_holdout)
    check_config_frozen()
    check_rerun(previous_runs(), arguments.rerun_reason)
    config = load_config()
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": git_commit(),
             "working_tree_clean": working_tree_clean(), "config_sha256": config_hash(),
             "config_matches_tag": TAG, "reason": arguments.rerun_reason or "first run"}

    run = run_holdout(arguments.unlock_holdout, config)
    entry |= {"holdout_matches": len(run.fold.test), "last_match_date": str(run.fold.test["date"].max().date())}
    metrics = metrics_table(run)
    by_name = metrics.set_index("predictor")["log_loss"]
    if by_name["final model"] < by_name["bookmaker"]:
        append_run(entry | {"outcome": "TRIPWIRE: model log loss beats the bookmaker; stopped before reporting"})
        print(f"TRIPWIRE: final model {by_name['final model']:.4f} beats bookmaker {by_name['bookmaker']:.4f}. "
              "Stop and audit before reporting.")
        return 1

    paired = paired_table(run, BASELINES)
    confusion = confusion_matrix(run.forecasts["final model"], run.results)
    confidence = subset_table({"final model": run.forecasts["final model"], "bookmaker": run.forecasts["bookmaker"]},
                              run.results)
    noise = noise_check(run, REPORTING_AVERAGE)
    metrics.to_csv(REPORTS_DIR / "stage10_holdout.csv", index=False)
    confidence.to_csv(REPORTS_DIR / "stage10_confidence.csv", index=False)
    predictions = run.fold.test[["date", "home", "away", "result"]].join(
        run.forecasts["final model"].add_prefix("model_")).join(run.forecasts["bookmaker"].add_prefix("bookmaker_"))
    predictions.to_csv(REPORTS_DIR / "stage10_predictions.csv", index=False)
    (REPORTS_DIR / "stage10_holdout.md").write_text(report(entry, metrics, paired, confusion, confidence, noise),
                                                     encoding="utf-8")
    append_run(entry | {"outcome": "reported", "final_model_log_loss": noise["holdout_log_loss"]})

    for title, frame in [("Holdout metrics", metrics), ("Paired difference", paired),
                         ("Confusion matrix (rows actual)", confusion.reset_index()), ("Confidence", confidence)]:
        print(f"\n{title}\n{frame.to_string(index=False, float_format='{:.4f}'.format)}")
    print(f"\nNoise: {noise}")
    print(f"Run log: {entry}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
