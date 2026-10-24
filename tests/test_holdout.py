"""Holdout guards. These tests never run the holdout evaluation itself."""

import shutil

import pytest

import src.holdout as holdout
from scripts.evaluate_holdout import check_rerun, main, parse
from src.final_model import CONFIG_PATH
from src.holdout import ConfigChangedError, check_config_frozen, frozen_config_bytes, run_holdout
from src.splits import HoldoutLockedError

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


def test_evaluation_refuses_without_the_unlock_flag(monkeypatch):
    touched: list[str] = []
    monkeypatch.setattr(holdout, "load_evaluation_matches", lambda **_: touched.append("matches"))
    with pytest.raises(HoldoutLockedError, match="--unlock-holdout"):
        main([])
    with pytest.raises(HoldoutLockedError):
        run_holdout(False, {})
    assert touched == []  # refused before reading any data


def test_unlock_flag_is_parsed():
    assert parse(["--unlock-holdout"]).unlock_holdout
    assert not parse([]).unlock_holdout


@needs_git
def test_config_is_byte_identical_to_the_tagged_one():
    assert CONFIG_PATH.read_bytes() == frozen_config_bytes()
    check_config_frozen()


@needs_git
def test_evaluation_aborts_if_the_config_changed(tmp_path):
    edited = tmp_path / "final_model.json"
    edited.write_bytes(CONFIG_PATH.read_bytes().replace(b'"C": 0.03', b'"C": 0.1'))
    with pytest.raises(ConfigChangedError):
        check_config_frozen(edited)


def test_a_second_run_needs_a_reason():
    check_rerun([], None)
    check_rerun([{"timestamp": "earlier"}], "fixed a bug in the report writer")
    with pytest.raises(RuntimeError, match="--rerun-reason"):
        check_rerun([{"timestamp": "earlier"}], None)
