"""Offline lookups and label text for the Streamlit app.

Every accuracy comes from a file in reports/ (Stage 9 pooled, Stage 10 holdout, the forward
score) and is always shown with its match count. Nothing here makes a network call.
"""

from pathlib import Path

import pandas as pd

from src.confidence import MIN_RELIABLE
from src.config import REPORTS_DIR
from src.forward import MIN_MATCHES_TO_CONCLUDE, UK, read_log

CONFIDENCE_LABEL_THRESHOLD = 0.60
LABEL_THRESHOLDS = (0.60, 0.65)
TUNED_SEASONS = "2016-17 to 2024-25"
HOLDOUT_LABEL = "2025-26 holdout"
SEASON_NOTE = "Season-to-season accuracy varies by several points; a season is 380 matches."
FORWARD_SCORE_PATH = REPORTS_DIR / "forward_score.csv"


def with_count(accuracy: float, matches: int) -> str:
    """An accuracy, always with its match count."""
    return f"{accuracy:.1%} ({matches} matches)"


def tuning_seasons_accuracy() -> dict[str, float]:
    """Pooled final-model accuracy over 2016-17..2024-25 (Stage 9, unscaled forecasts)."""
    raw = pd.read_csv(REPORTS_DIR / "stage9_calibration.csv")
    raw = raw[raw["forecast"] == "raw"]
    matches = int(raw["matches"].sum())
    return {"accuracy": float((raw["accuracy"] * raw["matches"]).sum() / matches), "matches": matches}


def holdout_accuracy() -> dict[str, dict[str, float]]:
    """Final-model and bookmaker accuracy on the 2025-26 holdout (Stage 10)."""
    table = pd.read_csv(REPORTS_DIR / "stage10_holdout.csv").set_index("predictor")
    return {name: {"accuracy": float(table.loc[name, "accuracy"]), "matches": int(table.loc[name, "matches"])}
            for name in ("final model", "bookmaker")}


def forward_record(path: Path = FORWARD_SCORE_PATH) -> dict[str, dict[str, float]]:
    """Forward-test accuracy per predictor from the last scripts.score_forward run (empty if none)."""
    if not path.exists():
        return {}
    table = pd.read_csv(path)
    if table.empty or "accuracy" not in table:
        return {}
    return {row["predictor"]: {"accuracy": float(row["accuracy"]), "matches": int(row["matches"])}
            for _, row in table.iterrows()}


def forward_line(record: dict[str, dict[str, float]]) -> str:
    if not record:
        return "Forward-test record (2026-27): no scored matches yet (n=0); too few matches to conclude."
    model, bookmaker = record["final model"], record["bookmaker"]
    line = (f"Forward-test record (2026-27): model {with_count(model['accuracy'], model['matches'])}, "
            f"bookmaker {with_count(bookmaker['accuracy'], bookmaker['matches'])}")
    return line + ("; too few matches to conclude." if model["matches"] < MIN_MATCHES_TO_CONCLUDE else ".")


def limits_lines(record_path: Path = FORWARD_SCORE_PATH) -> list[str]:
    """The Limits panel, every figure read from reports/."""
    tuned, holdout = tuning_seasons_accuracy(), holdout_accuracy()
    model, bookmaker = holdout["final model"], holdout["bookmaker"]
    return [
        "No injury, suspension or lineup data: the model only knows results and match statistics.",
        f"Accuracy, seasons used in tuning ({TUNED_SEASONS}): {with_count(tuned['accuracy'], tuned['matches'])}.",
        f"Accuracy, {HOLDOUT_LABEL}: model {with_count(model['accuracy'], model['matches'])}, "
        f"bookmaker {with_count(bookmaker['accuracy'], bookmaker['matches'])}.",
        forward_line(forward_record(record_path)),
        SEASON_NOTE,
    ]


def threshold_row(path: Path, top_threshold: float) -> pd.Series:
    table = pd.read_csv(path)
    return table[(table["predictor"] == "final model")
                 & (table["subset"] == f"top probability > {top_threshold:.2f}")].iloc[0]


def confidence_figures(top_probability: float) -> dict[str, float] | None:
    """Pooled (Stage 9) and holdout (Stage 10) accuracy at the highest label threshold exceeded."""
    exceeded = [threshold for threshold in LABEL_THRESHOLDS if top_probability > threshold]
    if not exceeded:
        return None
    threshold = max(exceeded)
    pooled = threshold_row(REPORTS_DIR / "stage9_confidence.csv", threshold)
    holdout = threshold_row(REPORTS_DIR / "stage10_confidence.csv", threshold)
    return {"threshold": threshold, "pooled_accuracy": float(pooled["accuracy"]), "pooled_matches": int(pooled["matches"]),
            "holdout_accuracy": float(holdout["accuracy"]), "holdout_matches": int(holdout["matches"])}


def confidence_label(top_probability: float) -> list[str]:
    """Lines for the confidence label next to the top probability."""
    figures = confidence_figures(top_probability)
    if figures is None:
        return [f"Top probability is {CONFIDENCE_LABEL_THRESHOLD:.2f} or below: a low-confidence match."]
    threshold = figures["threshold"]
    pooled = (f"Above {threshold:.2f}, {TUNED_SEASONS}: right {with_count(figures['pooled_accuracy'], figures['pooled_matches'])}; "
              "includes seasons the model was tuned on.")
    if figures["holdout_matches"] >= MIN_RELIABLE:
        holdout = (f"Above {threshold:.2f}, {HOLDOUT_LABEL}: right "
                   f"{with_count(figures['holdout_accuracy'], figures['holdout_matches'])}.")
    else:
        holdout = f"holdout: too few matches (n={figures['holdout_matches']})"
    return [pooled, holdout]


def equal_coverage_comparison() -> pd.DataFrame:
    """Model and bookmaker accuracy on their own most confident 10/20/30% (Stage 9), with counts."""
    table = pd.read_csv(REPORTS_DIR / "stage9_confidence.csv")
    coverage = table[table["subset"].str.startswith("most confident")]
    wide = coverage.pivot(index="subset", columns="predictor", values="accuracy")
    counts = coverage.groupby("subset")["matches"].first()
    return wide.assign(matches=counts).reset_index()[["subset", "final model", "bookmaker", "matches"]]


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
