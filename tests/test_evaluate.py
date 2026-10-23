import math

import pandas as pd
import pytest

from src.baselines import BASELINES, uniform
from src.data import POST_MATCH_COLUMNS
from src.evaluate import format_report, format_table, leakage_alarms, save_table, walk_forward, with_average
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


def metrics_table(rows: list[tuple[str, str, int, float, float]]) -> pd.DataFrame:
    """Rows of (predictor, season, matches, log loss, accuracy); RPS mirrors log loss."""
    table = pd.DataFrame(rows, columns=["predictor", "season", "matches", "log_loss", "accuracy"])
    return table.assign(rps=table["log_loss"])[["predictor", "season", "matches", "log_loss", "rps", "accuracy"]]


def test_average_row_is_the_match_weighted_pooled_score():
    table = with_average(metrics_table([("m", "2015-16", 10, 1.0, 0.4), ("m", "2016-17", 30, 1.0, 0.6)]))
    average = table[table["season"] == "average"].iloc[0]
    assert average["matches"] == 40
    assert average["accuracy"] == pytest.approx(0.55)


def test_single_season_above_58_percent_does_not_trip_the_wire():
    table = metrics_table([
        ("bookmaker", "2015-16", 380, 0.95, 0.61), ("bookmaker", "2016-17", 380, 0.95, 0.52),
        ("model", "2015-16", 380, 0.97, 0.60), ("model", "2016-17", 380, 0.97, 0.50),
    ])
    assert leakage_alarms(with_average(table)).empty


def test_pooled_accuracy_above_58_percent_trips_the_wire():
    table = metrics_table([("model", "2015-16", 380, 0.97, 0.60), ("model", "2016-17", 380, 0.97, 0.59)])
    alarms = leakage_alarms(with_average(table))
    assert alarms["predictor"].tolist() == ["model"]
    assert alarms["reason"].iloc[0] == "pooled accuracy above 58%"
    assert "LEAKAGE TRIPWIRE" in format_report(table)


def test_beating_the_bookmakers_pooled_log_loss_trips_the_wire():
    table = metrics_table([
        ("bookmaker", "2015-16", 380, 0.96, 0.55), ("model", "2015-16", 380, 0.95, 0.54),
        ("other", "2015-16", 380, 0.97, 0.53),
    ])
    alarms = leakage_alarms(table)
    assert alarms["predictor"].tolist() == ["model"]
    assert alarms["reason"].iloc[0] == "pooled log loss beats the bookmaker"


def test_report_without_alarm_lists_proper_scores_before_accuracy():
    report = format_report(metrics_table([("m", "2015-16", 380, 1.0, 0.50)]))
    assert "LEAKAGE TRIPWIRE" not in report
    assert report.index("Log loss") < report.index("Ranked probability") < report.index("Accuracy")


def test_infinite_log_loss_is_reported_as_na(tmp_path):
    table = with_average(metrics_table([("always home", "2015-16", 380, math.inf, 0.45)]).assign(rps=0.44))
    assert "n/a" in format_table(table)
    assert "inf" not in format_table(table) + format_report(table)
    saved = pd.read_csv(save_table(table, tmp_path / "metrics.csv"), keep_default_na=False)
    assert saved["log_loss"].tolist() == ["n/a", "n/a"]
    assert saved["rps"].tolist() == pytest.approx([0.44, 0.44])
    assert saved["accuracy"].tolist() == pytest.approx([0.45, 0.45])
