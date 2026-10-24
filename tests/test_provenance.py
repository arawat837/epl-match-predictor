"""reports/forward_provenance.json: rebuilt from the log, git and code exported with git archive."""

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.config import MATCHES_PATH, PROJECT_ROOT, REPORTS_DIR
from src.forward import read_log
from src.provenance import (FORWARD_CODE, code_commit, export_commit, first_batch, forward_provenance, has_file,
                            logged_day, stage_inputs)

RECORD = REPORTS_DIR / "forward_provenance.json"
needs_git = pytest.mark.skipif(
    subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True).returncode != 0,
    reason="needs the git history")


def committed_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def unix_text(content: bytes) -> str:
    return content.decode("utf-8").replace("\r\n", "\n")


def test_first_batch_is_the_rows_with_the_earliest_prediction_time():
    log = pd.DataFrame({"predicted_at": ["2026-10-31T09:00:00+00:00", "2026-10-24T00:53:30+00:00",
                                         "2026-10-24T00:53:30+00:00"], "home": ["C", "A", "B"]})
    assert first_batch(log)["home"].tolist() == ["A", "B"]


def test_inputs_are_the_batch_and_the_matches_dated_before_its_uk_logging_day(tmp_path):
    batch = pd.DataFrame({"predicted_at": ["2026-10-24T23:30:00+00:00"], "home": ["A"]})  # 00:30 BST on the 25th
    assert logged_day(batch) == pd.Timestamp("2026-10-25")
    matches = pd.DataFrame({"date": pd.to_datetime(["2026-10-24", "2026-10-25"]), "home": ["A", "B"]})
    matches.to_parquet(tmp_path / "matches.parquet", index=False)
    stage_inputs(tmp_path / "tree", batch, tmp_path / "matches.parquet")
    staged = pd.read_parquet(tmp_path / "tree" / "data" / "processed" / "matches.parquet")
    assert staged["date"].tolist() == [pd.Timestamp("2026-10-24")]
    assert pd.read_csv(tmp_path / "tree" / "data" / "forward" / "predictions_log.csv").equals(batch)


@needs_git
def test_the_first_batch_names_a_commit_without_the_forward_code():
    logged = first_batch(read_log())["git_commit"].iloc[0]
    assert not has_file(logged, FORWARD_CODE)
    assert code_commit(logged).startswith(committed_record()["code_commit"])


@needs_git
def test_export_is_the_committed_code_not_the_working_tree(tmp_path):
    commit = committed_record()["code_commit"]
    export_commit(commit, tmp_path)
    committed = subprocess.run(["git", "show", f"{commit}:{FORWARD_CODE}"], cwd=PROJECT_ROOT, capture_output=True,
                               check=True).stdout
    exported = (tmp_path / FORWARD_CODE).read_bytes()
    assert unix_text(exported) == unix_text(committed)
    assert unix_text(exported) != unix_text((PROJECT_ROOT / FORWARD_CODE).read_bytes())  # changed since
    assert not (tmp_path / "data").exists()


@needs_git
@pytest.mark.skipif(not MATCHES_PATH.exists(), reason="run `python -m scripts.build_dataset` first")
def test_rerun_on_two_fixtures_reproduces_the_committed_record():
    record, notes = forward_provenance(limit=2)
    assert record == committed_record() | {"recompute_fixtures": 2}
    assert not notes["logged_commit_has_forward_code"]
    assert not Path(notes["code_path"]).resolve().is_relative_to(PROJECT_ROOT)
