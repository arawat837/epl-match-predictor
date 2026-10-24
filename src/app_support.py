"""Offline lookups for the Streamlit app: historical accuracy, confidence and the forward record.

Everything is read from files already on disk (reports/, data/processed/, data/forward/); nothing
here makes a network call.
"""

import pandas as pd

from src.config import REPORTS_DIR
from src.forward import UK, read_log

CONFIDENCE_LABEL_THRESHOLD = 0.60
LABEL_THRESHOLDS = (0.60, 0.65)


def historical_accuracy() -> tuple[int, int]:
    """(correct, matches) for the final model over 2016-17..2024-25 (Stage 9) plus the 2025-26 holdout."""
    calibration = pd.read_csv(REPORTS_DIR / "stage9_calibration.csv")
    raw = calibration[calibration["forecast"] == "raw"]
    holdout = pd.read_csv(REPORTS_DIR / "stage10_holdout.csv").set_index("predictor").loc["final model"]
    correct = (raw["accuracy"] * raw["matches"]).sum() + holdout["accuracy"] * holdout["matches"]
    return int(round(correct)), int(raw["matches"].sum() + holdout["matches"])


def confidence_lookup(top_probability: float) -> dict[str, object] | None:
    """Stage 9 pooled accuracy at the highest threshold (0.60 or 0.65) the forecast exceeds."""
    exceeded = [threshold for threshold in LABEL_THRESHOLDS if top_probability > threshold]
    if not exceeded:
        return None
    table = pd.read_csv(REPORTS_DIR / "stage9_confidence.csv")
    row = table[(table["predictor"] == "final model")
                & (table["subset"] == f"top probability > {max(exceeded):.2f}")].iloc[0]
    return {"threshold": max(exceeded), "accuracy": float(row["accuracy"]), "matches": int(row["matches"])}


def equal_coverage_comparison() -> pd.DataFrame:
    """Model and bookmaker accuracy on their own most confident 10/20/30% (Stage 9, pooled)."""
    table = pd.read_csv(REPORTS_DIR / "stage9_confidence.csv")
    coverage = table[table["subset"].str.startswith("most confident")]
    return coverage.pivot(index="subset", columns="predictor", values="accuracy").reset_index()


def upcoming_fixtures(now: pd.Timestamp, log: pd.DataFrame | None = None) -> pd.DataFrame:
    """The latest logged prediction for every fixture that hasn't kicked off yet."""
    log = read_log() if log is None else log
    kickoff = pd.to_datetime(log["kickoff"], utc=True)
    future = log[kickoff > now].assign(kickoff=kickoff[kickoff > now])
    latest = future.drop_duplicates(["home", "away"], keep="last").sort_values("kickoff")
    return latest.assign(label=latest["kickoff"].dt.tz_convert(UK).dt.strftime("%a %d %b %H:%M")
                         + "  " + latest["home"] + " v " + latest["away"])


def latest_season_teams(played: pd.DataFrame) -> list[str]:
    latest = played[played["season"] == played["season"].max()]
    return sorted(set(latest["home"]) | set(latest["away"]))
