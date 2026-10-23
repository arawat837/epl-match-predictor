import pandas as pd
import pytest

from src.baselines import BASELINES, uniform
from src.data import POST_MATCH_COLUMNS
from src.evaluate import format_report, leakage_alarms, walk_forward, with_average
from src.splits import walk_forward_splits


def test_predictors_never_see_the_test_matches_post_match_columns(make_seasons):
    seen: list[set[str]] = []

    def spy(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        seen.append(set(test.columns))
        return uniform(train, test)

    walk_forward({"spy": spy}, walk_forward_splits(make_seasons([2014, 2015, 2016])))
    assert len(seen) == 2
    assert all(columns.isdisjoint(POST_MATCH_COLUMNS) for columns in seen)


def test_walk_forward_has_one_row_per_predictor_and_season(make_seasons):
    table = walk_forward(BASELINES, walk_forward_splits(make_seasons([2014, 2015, 2016])))
    assert len(table) == len(BASELINES) * 2
    assert list(table.columns) == ["predictor", "season", "matches", "log_loss", "rps", "accuracy"]


def metrics_table(rows: list[tuple[str, str, int, float]]) -> pd.DataFrame:
    """Rows of (predictor, season, matches, accuracy); log loss and RPS mirror accuracy."""
    table = pd.DataFrame(rows, columns=["predictor", "season", "matches", "accuracy"])
    return table.assign(log_loss=table["accuracy"], rps=table["accuracy"])[
        ["predictor", "season", "matches", "log_loss", "rps", "accuracy"]]


def test_average_row_is_the_match_weighted_pooled_score():
    table = with_average(metrics_table([("m", "2015-16", 10, 0.4), ("m", "2016-17", 30, 0.6)]))
    average = table[table["season"] == "average"].iloc[0]
    assert average["matches"] == 40
    assert average["accuracy"] == pytest.approx(0.55)


def test_leakage_alarm_flags_accuracy_strictly_above_58_percent():
    table = metrics_table([("m", "2015-16", 380, 0.58), ("m", "2016-17", 380, 0.59)])
    assert leakage_alarms(table)["season"].tolist() == ["2016-17"]
    assert "LEAKAGE ALARM" in format_report(table)


def test_report_without_alarm_lists_proper_scores_before_accuracy():
    report = format_report(metrics_table([("m", "2015-16", 380, 0.50)]))
    assert "LEAKAGE ALARM" not in report
    assert report.index("Log loss") < report.index("Ranked probability") < report.index("Accuracy")
