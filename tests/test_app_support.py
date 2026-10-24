"""App labels: every number comes from reports/ and every accuracy carries its match count."""

import re
import shutil

import pandas as pd
import pytest

import src.app_support as app_support
from src.app_support import (SEASON_NOTE, confidence_figures, confidence_label, forward_line, forward_record,
                             holdout_accuracy, limits_lines, tuning_seasons_accuracy, with_count)
from src.config import PROJECT_ROOT, REPORTS_DIR

needs_reports = pytest.mark.skipif(not all((REPORTS_DIR / name).exists() for name in (
    "stage9_calibration.csv", "stage9_confidence.csv", "stage10_holdout.csv", "stage10_confidence.csv")),
    reason="needs the Stage 9 and Stage 10 reports")
PERCENT_WITHOUT_COUNT = re.compile(r"\d+(?:\.\d+)?%(?! \(\d+ matches\))")


@needs_reports
def test_tuning_seasons_accuracy_equals_the_stage9_report():
    raw = pd.read_csv(REPORTS_DIR / "stage9_calibration.csv").query("forecast == 'raw'")
    expected = (raw["accuracy"] * raw["matches"]).sum() / raw["matches"].sum()
    assert tuning_seasons_accuracy() == {"accuracy": pytest.approx(expected), "matches": int(raw["matches"].sum())}


@needs_reports
def test_holdout_accuracy_equals_the_stage10_report():
    table = pd.read_csv(REPORTS_DIR / "stage10_holdout.csv").set_index("predictor")
    for name, figures in holdout_accuracy().items():
        assert figures == {"accuracy": pytest.approx(table.loc[name, "accuracy"]), "matches": table.loc[name, "matches"]}


@needs_reports
@pytest.mark.parametrize("top, threshold", [(0.64, 0.60), (0.72, 0.65)])
def test_confidence_figures_equal_the_report_rows(top, threshold):
    def row(name: str) -> pd.Series:
        table = pd.read_csv(REPORTS_DIR / name)
        return table[(table["predictor"] == "final model") & (table["subset"] == f"top probability > {threshold:.2f}")].iloc[0]
    figures = confidence_figures(top)
    assert figures["threshold"] == threshold
    assert (figures["pooled_accuracy"], figures["pooled_matches"]) == (row("stage9_confidence.csv")["accuracy"],
                                                                       row("stage9_confidence.csv")["matches"])
    assert (figures["holdout_accuracy"], figures["holdout_matches"]) == (row("stage10_confidence.csv")["accuracy"],
                                                                         row("stage10_confidence.csv")["matches"])
    pooled, holdout = confidence_label(top)
    assert with_count(figures["pooled_accuracy"], figures["pooled_matches"]) in pooled
    assert "includes seasons the model was tuned on" in pooled
    assert holdout == f"holdout: too few matches (n={figures['holdout_matches']})"  # under 100 at both thresholds


@needs_reports
def test_holdout_figure_is_shown_once_it_has_100_matches(tmp_path, monkeypatch):
    for name in ("stage9_confidence.csv", "stage10_confidence.csv"):
        shutil.copy(REPORTS_DIR / name, tmp_path / name)
    holdout = pd.read_csv(tmp_path / "stage10_confidence.csv")
    holdout.loc[holdout["subset"] == "top probability > 0.60", "matches"] = 150
    holdout.to_csv(tmp_path / "stage10_confidence.csv", index=False)
    monkeypatch.setattr(app_support, "REPORTS_DIR", tmp_path)
    accuracy = holdout.loc[(holdout["predictor"] == "final model") & (holdout["subset"] == "top probability > 0.60"),
                           "accuracy"].iloc[0]
    assert confidence_label(0.62)[1] == f"Above 0.60, 2025-26 holdout: right {with_count(accuracy, 150)}."


def test_low_confidence_label():
    assert confidence_label(0.55) == ["Top probability is 0.60 or below: a low-confidence match."]


def test_forward_line_reads_counts_and_says_too_few(tmp_path):
    assert "no scored matches yet (n=0)" in forward_line(forward_record(tmp_path / "missing.csv"))
    path = tmp_path / "forward_score.csv"
    pd.DataFrame({"predictor": ["final model", "bookmaker"], "matches": [12, 12],
                  "accuracy": [0.5, 7 / 12]}).to_csv(path, index=False)
    line = forward_line(forward_record(path))
    assert "model 50.0% (12 matches)" in line and "bookmaker 58.3% (12 matches)" in line
    assert line.endswith("too few matches to conclude.")


@needs_reports
def test_every_percentage_in_the_labels_has_its_count():
    lines = limits_lines() + confidence_label(0.64) + confidence_label(0.72)
    assert SEASON_NOTE in lines
    assert any(line.startswith("Accuracy, seasons used in tuning") for line in lines)
    assert any(line.startswith("Accuracy, 2025-26 holdout: model") and "bookmaker" in line for line in lines)
    assert any(line.startswith("Forward-test record") for line in lines)
    assert [match for line in lines for match in PERCENT_WITHOUT_COUNT.findall(line)] == []


def test_app_source_has_no_hard_coded_accuracy():
    source = (PROJECT_ROOT / "app" / "app.py").read_text(encoding="utf-8")
    without_format_fields = re.sub(r"\{[^{}]*\}", "", source)
    assert re.findall(r"\d+(?:\.\d+)?\s*%", without_format_fields) == []
    assert re.findall(r"\b0\.\d+", without_format_fields) == []
