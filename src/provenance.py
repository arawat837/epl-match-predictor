"""reports/forward_provenance.json: when the first forward predictions were logged, when their code
was committed, and whether that committed code reproduces them.

The recompute runs the code exported with `git archive`, never the working tree's src/: the
commit named in the log, or, when that commit has no forward code (the first batch was logged
from the working tree before the Stage 11 code was committed), the commit that added
src/forward.py. It runs offline on the matches played before the batch was logged.
"""

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import MATCHES_PATH, PROJECT_ROOT
from src.forward import LOG_PATH, UK, read_log, season_of

FORWARD_CODE = "src/forward.py"
EXPORTED = ["src", "config"]
SOURCES = ("prediction log data/forward/predictions_log.csv; git log/rev-parse for the commit; "
           "recompute by running the code exported with git archive at the commit, offline, on the saved data")

# Runs inside the exported tree (its src/ comes first on the path): recompute every logged row.
RECOMPUTE_PROGRAM = """
import json
import numpy as np
import pandas as pd
import src
from src.final_model import elo_params, load_config, predictor
from src.forward import (fixture_features, fixture_row, forecast, inputs_hash, load_played_matches, read_log,
                         season_pipeline, training_table)

log, matches = read_log(), load_played_matches()
config = load_config()
elo, model = elo_params(config), predictor(config)
table = training_table(matches, elo)
differences, unchanged = [], []
for _, logged in log.iterrows():
    row = fixture_row(logged["home"], logged["away"], pd.Timestamp(logged["kickoff"]))
    features = fixture_features(matches, row, elo)
    frame = features[model.columns].astype(float).to_frame().T
    probabilities = forecast(season_pipeline(table, row["season"].iloc[0], model), model.columns, frame).iloc[0]
    logged_probabilities = logged[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    differences.append(float(np.max(np.abs(probabilities.to_numpy() - logged_probabilities))))
    unchanged.append(inputs_hash(features, model.columns) == logged["inputs_hash"])
print(json.dumps({"code_path": src.__file__, "fixtures": len(log), "inputs_unchanged": all(unchanged),
                  "max_abs_difference": max(differences)}))
"""


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def first_batch(log: pd.DataFrame) -> pd.DataFrame:
    """The rows logged at the earliest prediction time."""
    return log[log["predicted_at"] == log["predicted_at"].min()].reset_index(drop=True)


def has_file(commit: str, path: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=PROJECT_ROOT,
                          capture_output=True).returncode == 0


def commit_that_added(path: str) -> str:
    return git("log", "--diff-filter=A", "--format=%H", "--", path).splitlines()[-1]


def code_commit(logged_commit: str) -> str:
    """The commit whose code is recomputed: the logged one if it has the forward code, else the
    commit that added the forward code."""
    return logged_commit if has_file(logged_commit, FORWARD_CODE) else commit_that_added(FORWARD_CODE)


def export_commit(commit: str, directory: Path) -> None:
    """Write the commit's src/ and config/ into `directory` with git archive."""
    archive = subprocess.run(["git", "archive", "--format=tar", commit, *EXPORTED], cwd=PROJECT_ROOT,
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(directory, filter="data")


def logged_day(batch: pd.DataFrame) -> pd.Timestamp:
    """The UK calendar day on which the batch was logged."""
    return pd.Timestamp(batch["predicted_at"].min()).tz_convert(UK).tz_localize(None).normalize()


def stage_inputs(directory: Path, batch: pd.DataFrame, matches_path: Path) -> None:
    """Put the batch's log rows, and the matches dated before the day it was logged, where the
    exported code reads them."""
    matches = pd.read_parquet(matches_path)
    (directory / "data" / "processed").mkdir(parents=True, exist_ok=True)
    matches[matches["date"] < logged_day(batch)].to_parquet(directory / "data" / "processed" / "matches.parquet",
                                                            index=False)
    (directory / "data" / "forward").mkdir(parents=True, exist_ok=True)
    batch.to_csv(directory / "data" / "forward" / "predictions_log.csv", index=False)


def recompute(commit: str, batch: pd.DataFrame, matches_path: Path = MATCHES_PATH) -> dict[str, object]:
    """Recompute the batch with the commit's exported code; raises if the working tree's src/ was used."""
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        export_commit(commit, directory)
        stage_inputs(directory, batch, matches_path)
        environment = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
        output = subprocess.run([sys.executable, "-c", RECOMPUTE_PROGRAM], cwd=directory, env=environment,
                                capture_output=True, text=True, check=True).stdout
        result = json.loads(output.strip().splitlines()[-1])
        if not Path(result["code_path"]).resolve().is_relative_to(directory.resolve()):
            raise RuntimeError(f"recompute imported {result['code_path']}, not the exported code")
    return result


def committed_at(commit: str) -> datetime:
    return datetime.fromisoformat(git("log", "-1", "--format=%cI", commit)).astimezone(timezone.utc)


def forward_provenance(log_path: Path = LOG_PATH, matches_path: Path = MATCHES_PATH,
                       limit: int | None = None) -> tuple[dict[str, object], dict[str, object]]:
    """The provenance record of the first logged batch (recomputing its first `limit` rows, all
    if None), and notes: whether the logged commit has the forward code, and the code path used."""
    batch = first_batch(read_log(log_path))
    logged, first_kickoff = batch["git_commit"].iloc[0], pd.to_datetime(batch["kickoff"], utc=True).min()
    commit = code_commit(logged)
    recomputed = recompute(commit, batch if limit is None else batch.head(limit), matches_path)
    short = git("rev-parse", "--short", commit)
    record = {
        "first_batch_predictions": len(batch),
        "first_logged_at_utc": pd.Timestamp(batch["predicted_at"].min()).isoformat(),
        "logged_git_commit": logged,
        "code_commit": short,
        "code_committed_at_utc": committed_at(commit).isoformat(),
        "first_kickoff_utc": first_kickoff.isoformat(),
        "forward_season": season_of(first_kickoff.tz_convert(UK).tz_localize(None)),
        "recompute_code_commit": short,
        "recompute_fixtures": recomputed["fixtures"],
        "recompute_inputs_unchanged": recomputed["inputs_unchanged"],
        "recompute_max_abs_difference": recomputed["max_abs_difference"],
        "sources": SOURCES,
    }
    notes = {"logged_commit_has_forward_code": has_file(logged, FORWARD_CODE), "code_path": recomputed["code_path"]}
    return record, notes


def record_text(record: dict[str, object]) -> str:
    return json.dumps(record, indent=2)
