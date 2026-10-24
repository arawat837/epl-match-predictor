"""Forward test of the frozen final model on the current season.

The current season (2026-27) is the forward-test season: it is used only to predict upcoming
fixtures and to score those predictions once played, never for model selection. As for the
holdout, the model is fitted once on every match before the season and not refitted within it.

Features for a fixture come from the Stage 4 code unchanged: the fixture is appended to the
played matches with placeholder stats, which never reach its own features (tests/test_leakage.py).
The prediction log is append-only.
"""

import hashlib
import io
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.config import MATCHES_PATH, PROJECT_ROOT
from src.data import MATCH_COLUMNS, raw_path, read_raw_season
from src.dataset import join_features
from src.elo import EloParams
from src.features import build_features
from src.metrics import OUTCOMES, accuracy, log_losses, ranked_probability_score
from src.models import LogisticModel
from src.odds import implied_probabilities
from src.seasons import current_season, season_label
from src.teams import standardise_team_names
from src.tuning import paired_difference

FORWARD_DIR = PROJECT_ROOT / "data" / "forward"
LOG_PATH = FORWARD_DIR / "predictions_log.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
LOG_COLUMNS = ["predicted_at", "kickoff", "home", "away", "p_home", "p_draw", "p_away",
               "inputs_hash", "git_commit", "config_hash"]
UK = "Europe/London"
PLACEHOLDER = {"FTHG": 0, "FTAG": 0, "result": "D", "HS": 0, "AS": 0, "HST": 0, "AST": 0}
MIN_MATCHES_TO_CONCLUDE = 100


class PastKickoffError(ValueError):
    """Raised when asked to log a prediction for a fixture that has already kicked off."""


def load_played_matches(path: Path = MATCHES_PATH) -> pd.DataFrame:
    """Every played match, the current season included (forward-test use only)."""
    return pd.read_parquet(path)


def season_of(day: pd.Timestamp) -> str:
    return season_label(current_season(day.date()))


def uk_kickoff(dates: pd.Series, times: pd.Series) -> pd.Series:
    """UTC kickoff from football-data's day-first date and UK local time (midnight if no time)."""
    local = pd.to_datetime(dates + " " + times.fillna("00:00"), format="%d/%m/%Y %H:%M")
    return local.dt.tz_localize(UK).dt.tz_convert("UTC")


def parse_fixtures(content: bytes) -> pd.DataFrame:
    """Premier League rows of football-data's fixtures.csv: UTC kickoff, home, away."""
    raw = pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8-sig")
    league = raw[raw["Div"] == "E0"]
    return pd.DataFrame({"kickoff": uk_kickoff(league["Date"], league["Time"]),
                         "home": standardise_team_names(league["HomeTeam"]),
                         "away": standardise_team_names(league["AwayTeam"])}).reset_index(drop=True)


def fixture_row(home: str, away: str, kickoff: pd.Timestamp) -> pd.DataFrame:
    """A match-table row for an unplayed fixture, with placeholder stats and no odds."""
    day = kickoff.tz_convert(UK).tz_localize(None).normalize()
    row = {"date": day, "season": season_of(day), "home": home, "away": away, **PLACEHOLDER,
           "odds_home": np.nan, "odds_draw": np.nan, "odds_away": np.nan, "odds_source": pd.NA}
    return pd.DataFrame([row])[MATCH_COLUMNS]


def fixture_features(played: pd.DataFrame, fixture: pd.DataFrame, elo: EloParams) -> pd.Series:
    """Stage 4 features for the fixture, computed from the played matches dated before it."""
    earlier = played[played["date"] < fixture["date"].iloc[0]]
    combined = pd.concat([earlier, fixture], ignore_index=True)
    return build_features(combined, elo).iloc[-1]


def training_table(played: pd.DataFrame, elo: EloParams) -> pd.DataFrame:
    """Played matches with their features (frozen Elo), burn-in dropped."""
    table = join_features(played, build_features(played, elo))
    return table[~table["burn_in"]].reset_index(drop=True)


def season_pipeline(table: pd.DataFrame, season: str, model: LogisticModel) -> Pipeline:
    """The final model fitted once on every match before `season`."""
    return model.fit(table[table["season"] < season], season)


def forecast(pipeline: Pipeline, columns: list[str], rows: pd.DataFrame) -> pd.DataFrame:
    """H/D/A probabilities for feature rows."""
    return pd.DataFrame(pipeline.predict_proba(rows[columns]), index=rows.index, columns=OUTCOMES)


def inputs_hash(features: pd.Series, columns: list[str]) -> str:
    """Fingerprint of a fixture's model inputs; it changes only when new results change them."""
    text = "|".join(f"{float(value):.10g}" for value in features[columns])
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def read_log(path: Path = LOG_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=LOG_COLUMNS)
    log = pd.read_csv(path, dtype={"inputs_hash": str, "git_commit": str, "config_hash": str})
    if list(log.columns) != LOG_COLUMNS:
        raise ValueError(f"{path} has columns {list(log.columns)}, expected {LOG_COLUMNS}")
    return log


def unchanged_since_logged(rows: pd.DataFrame, log: pd.DataFrame) -> pd.Series:
    """Rows whose fixture's latest logged prediction had the same inputs."""
    latest = log.drop_duplicates(["home", "away"], keep="last").set_index(["home", "away"])["inputs_hash"]
    keys = pd.MultiIndex.from_frame(rows[["home", "away"]])
    return pd.Series(latest.reindex(keys).to_numpy() == rows["inputs_hash"].to_numpy(), index=rows.index)


def append_log(rows: pd.DataFrame, now: datetime, path: Path = LOG_PATH) -> int:
    """Append predictions; never edits or removes existing rows. Refuses any fixture whose
    kickoff has passed, and skips fixtures whose inputs are unchanged since last logged."""
    past = rows[pd.to_datetime(rows["kickoff"], utc=True) <= pd.Timestamp(now)]
    if not past.empty:
        raise PastKickoffError(f"kickoff already passed for {past[['home', 'away']].values.tolist()}")
    fresh = rows[~unchanged_since_logged(rows, read_log(path))]
    if not fresh.empty:
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh[LOG_COLUMNS].to_csv(path, mode="a", header=not path.exists(), index=False)
    return len(fresh)


def actual_kickoffs(start_year: int) -> pd.DataFrame:
    """Played matches' actual UTC kickoffs from the season's football-data results file."""
    raw = read_raw_season(raw_path(start_year))
    return pd.DataFrame({"home": standardise_team_names(raw["HomeTeam"]),
                         "away": standardise_team_names(raw["AwayTeam"]),
                         "actual_kickoff": uk_kickoff(raw["Date"], raw["Time"])})


def scoreable(log: pd.DataFrame, played: pd.DataFrame, kickoffs: pd.DataFrame, season: str) -> pd.DataFrame:
    """Per played match of `season`: the latest logged prediction made before its actual
    kickoff, with the result and the bookmaker's odds from the results file."""
    results = played[played["season"] == season].merge(kickoffs, on=["home", "away"], how="left")
    logged_season = pd.to_datetime(log["kickoff"], utc=True).map(lambda kickoff: season_of(
        kickoff.tz_convert(UK).tz_localize(None)))
    joined = log[logged_season == season].merge(results, on=["home", "away"], how="inner")
    before = joined[pd.to_datetime(joined["predicted_at"], utc=True) < joined["actual_kickoff"]]
    return before.sort_values("predicted_at").drop_duplicates(["home", "away"], keep="last").reset_index(drop=True)


def standard_error(values: pd.Series) -> float:
    return float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else float("nan")


def forward_summary(scored: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Log loss, RPS and accuracy (with standard errors) for the model and the bookmaker on the
    same matches, plus a verdict line."""
    if scored.empty:
        return pd.DataFrame(columns=["predictor", "matches"]), (
            f"0 scored matches: too few matches to conclude (need {MIN_MATCHES_TO_CONCLUDE}).")
    results = scored["result"]
    predictors = {"final model": scored[["p_home", "p_draw", "p_away"]].set_axis(OUTCOMES, axis=1),
                  "bookmaker": implied_probabilities(scored)}
    rows, losses = [], {}
    for name, probabilities in predictors.items():
        losses[name] = log_losses(probabilities, results)
        rps = pd.Series([ranked_probability_score(probabilities.iloc[[i]], results.iloc[[i]]) for i in range(len(results))])
        correct = (probabilities.idxmax(axis=1) == results).astype(float)
        rows.append({"predictor": name, "matches": len(results),
                     "log_loss": losses[name].mean(), "log_loss_se": standard_error(losses[name]),
                     "rps": rps.mean(), "rps_se": standard_error(rps),
                     "accuracy": accuracy(probabilities, results), "accuracy_se": standard_error(correct)})
    difference, error = paired_difference(losses["final model"], losses["bookmaker"]) if len(results) > 1 else (np.nan, np.nan)
    verdict = (f"{len(results)} scored matches: too few matches to conclude (need {MIN_MATCHES_TO_CONCLUDE})."
               if len(results) < MIN_MATCHES_TO_CONCLUDE else f"{len(results)} scored matches.")
    return pd.DataFrame(rows), f"{verdict} Model minus bookmaker log loss {difference:+.4f} (SE {error:.4f})."
