"""Forward log, fixture features and forward scoring."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.config import MATCHES_PATH
from src.experiments import BASE_ELO
from src.features import build_features, feature_columns
from src.forward import (LOG_COLUMNS, PastKickoffError, append_log, fixture_features, fixture_row, forward_summary,
                         inputs_hash, parse_fixtures, read_log, scoreable)

NOW = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)


def log_rows(*rows: tuple[str, str, str, str]) -> pd.DataFrame:
    """Rows of (predicted_at, kickoff, home, away) with fixed probabilities; hash = home + away + kickoff."""
    frame = pd.DataFrame(rows, columns=["predicted_at", "kickoff", "home", "away"])
    return frame.assign(p_home=0.5, p_draw=0.3, p_away=0.2, inputs_hash=frame["home"] + frame["away"],
                        git_commit="abc", config_hash="def")[LOG_COLUMNS]


def test_logging_refuses_a_fixture_whose_kickoff_has_passed(tmp_path):
    path = tmp_path / "log.csv"
    rows = log_rows(("2026-10-24T09:00:00+00:00", "2026-10-24T08:59:00+00:00", "Arsenal", "Everton"))
    with pytest.raises(PastKickoffError, match="Arsenal"):
        append_log(rows, NOW, path)
    assert not path.exists()


def test_log_is_append_only_and_skips_unchanged_inputs(tmp_path):
    path = tmp_path / "log.csv"
    first = log_rows(("2026-10-24T09:00:00+00:00", "2026-10-25T14:00:00+00:00", "Arsenal", "Everton"))
    assert append_log(first, NOW, path) == 1
    before = path.read_bytes()

    assert append_log(first, NOW, path) == 0  # same inputs: nothing appended
    assert path.read_bytes() == before

    changed = first.assign(inputs_hash="new results arrived")
    another = log_rows(("2026-10-24T09:00:00+00:00", "2026-10-25T16:30:00+00:00", "Chelsea", "Tottenham"))
    assert append_log(pd.concat([changed, another]), NOW, path) == 2
    after = path.read_bytes()
    assert after.startswith(before)  # earlier rows untouched
    assert read_log(path)["inputs_hash"].tolist() == ["ArsenalEverton", "new results arrived", "ChelseaTottenham"]


def test_scoring_uses_the_latest_prediction_made_before_kickoff():
    log = pd.concat([
        log_rows(("2026-10-20T09:00:00+00:00", "2026-10-25T14:00:00+00:00", "Arsenal", "Everton")),
        log_rows(("2026-10-24T09:00:00+00:00", "2026-10-25T14:00:00+00:00", "Arsenal", "Everton")).assign(p_home=0.6, p_draw=0.2),
        log_rows(("2026-10-25T14:30:00+00:00", "2026-10-25T14:00:00+00:00", "Arsenal", "Everton")).assign(p_home=0.9, p_draw=0.05, p_away=0.05),
        log_rows(("2026-10-25T15:00:00+00:00", "2026-10-25T14:00:00+00:00", "Chelsea", "Tottenham")),
    ], ignore_index=True)
    played = pd.DataFrame({"season": "2026-27", "home": ["Arsenal", "Chelsea"], "away": ["Everton", "Tottenham"],
                           "date": pd.Timestamp("2026-10-25"), "result": ["H", "A"],
                           "odds_home": 1.5, "odds_draw": 4.0, "odds_away": 7.0})
    kickoffs = pd.DataFrame({"home": ["Arsenal", "Chelsea"], "away": ["Everton", "Tottenham"],
                             "actual_kickoff": pd.to_datetime(["2026-10-25T14:00:00Z", "2026-10-25T14:00:00Z"])})
    scored = scoreable(log, played, kickoffs, "2026-27")
    assert scored[["home", "p_home"]].values.tolist() == [["Arsenal", 0.6]]  # after-kickoff rows ignored


def test_summary_says_too_few_matches_below_100():
    scored = pd.DataFrame({"p_home": [0.5, 0.2], "p_draw": [0.3, 0.3], "p_away": [0.2, 0.5], "result": ["H", "A"],
                           "odds_home": [1.8, 4.0], "odds_draw": [3.5, 3.5], "odds_away": [4.5, 1.9]})
    table, verdict = forward_summary(scored)
    assert "too few matches to conclude" in verdict
    assert set(table["predictor"]) == {"final model", "bookmaker"}
    assert table["log_loss_se"].notna().all()


def test_fixtures_file_is_read_as_premier_league_rows_with_utc_kickoffs():
    content = ("Div,Date,Time,HomeTeam,AwayTeam\n"
               "E0,24/10/2026,12:30,Aston Villa,Man City\n"
               "E1,24/10/2026,15:00,Leicester,Stoke\n"
               "E0,26/12/2026,15:00,Man United,Nott'm Forest\n").encode()
    fixtures = parse_fixtures(content)
    assert fixtures[["home", "away"]].values.tolist() == [["Aston Villa", "Manchester City"],
                                                         ["Manchester United", "Nottingham Forest"]]
    assert fixtures["kickoff"].tolist() == [pd.Timestamp("2026-10-24T11:30:00Z"), pd.Timestamp("2026-12-26T15:00:00Z")]


CLOCK_CHANGE_FIXTURES = ("Div,Date,Time,HomeTeam,AwayTeam\n"
                         "E0,24/10/2026,12:30,Aston Villa,Man City\n"
                         "E0,24/10/2026,15:00,Arsenal,Everton\n"
                         "E0,24/10/2026,17:30,Chelsea,Tottenham\n"
                         "E0,25/10/2026,00:30,Burnley,Wolves\n"  # still BST: clocks go back at 02:00
                         "E0,25/10/2026,03:00,Leeds,Fulham\n"  # already GMT
                         "E0,25/10/2026,14:00,Crystal Palace,Newcastle\n"
                         "E0,25/10/2026,16:30,Sunderland,Leeds\n").encode()


def test_uk_times_use_the_london_zone_on_both_sides_of_the_clock_change():
    from zoneinfo import ZoneInfo
    from src.forward import UK

    assert UK == ZoneInfo("Europe/London")
    kickoffs = parse_fixtures(CLOCK_CHANGE_FIXTURES)["kickoff"]
    assert [kickoff.isoformat() for kickoff in kickoffs] == [
        "2026-10-24T11:30:00+00:00",  # Saturday 12:30 BST = UTC+1
        "2026-10-24T14:00:00+00:00",
        "2026-10-24T16:30:00+00:00",
        "2026-10-24T23:30:00+00:00",  # Sunday 00:30 BST is still Saturday in UTC
        "2026-10-25T03:00:00+00:00",  # Sunday 03:00 GMT = UTC+0
        "2026-10-25T14:00:00+00:00",  # Sunday 14:00 GMT
        "2026-10-25T16:30:00+00:00",
    ]
    assert [kickoff.tz_convert(UK).strftime("%d %H:%M") for kickoff in kickoffs] == [
        "24 12:30", "24 15:00", "24 17:30", "25 00:30", "25 03:00", "25 14:00", "25 16:30"]


def test_fixture_date_is_the_uk_calendar_date_across_the_change():
    late_saturday_utc = parse_fixtures(CLOCK_CHANGE_FIXTURES)["kickoff"].iloc[3]  # 23:30Z on the 24th
    assert fixture_row("Burnley", "Wolverhampton Wanderers", late_saturday_utc)["date"].iloc[0] == pd.Timestamp("2026-10-25")


def test_an_ambiguous_local_time_raises_instead_of_guessing():
    with pytest.raises(Exception, match="(?i)ambiguous"):
        parse_fixtures(b"Div,Date,Time,HomeTeam,AwayTeam\nE0,25/10/2026,01:30,Arsenal,Everton\n")


@pytest.mark.parametrize("now, refused", [
    ("2026-10-25T13:00:00Z", False),  # when a UTC+1 mistake would think kickoff had come
    ("2026-10-25T13:59:59Z", False),
    ("2026-10-25T14:00:00Z", True),  # Sunday 14:00 UK is 14:00Z
    ("2026-10-25T14:00:01Z", True),
])
def test_logging_around_sundays_1400z_kickoff(tmp_path, now, refused):
    fixture = parse_fixtures(CLOCK_CHANGE_FIXTURES).iloc[5]  # Crystal Palace v Newcastle, Sunday 14:00 UK
    rows = log_rows(("2026-10-25T09:00:00+00:00", fixture["kickoff"].isoformat(), fixture["home"], fixture["away"]))
    path = tmp_path / "log.csv"
    moment = pd.Timestamp(now).to_pydatetime()
    if refused:
        with pytest.raises(PastKickoffError):
            append_log(rows, moment, path)
        assert not path.exists()
    else:
        assert append_log(rows, moment, path) == 1


def test_inputs_hash_changes_only_with_the_inputs():
    features = pd.Series({"a": 1.0, "b": np.nan})
    assert inputs_hash(features, ["a", "b"]) == inputs_hash(features.copy(), ["a", "b"])
    assert inputs_hash(features, ["a", "b"]) != inputs_hash(features.replace(1.0, 1.5), ["a", "b"])


@pytest.mark.skipif(not MATCHES_PATH.exists(), reason="run `python -m scripts.build_dataset` first")
def test_fixture_features_equal_the_walk_forward_pipeline_for_the_last_20_played_matches():
    played = pd.read_parquet(MATCHES_PATH)
    walk_forward = build_features(played, BASE_ELO)
    columns = feature_columns(walk_forward)
    for index in played.sort_values("date").index[-20:]:
        match = played.loc[index]
        kickoff = pd.Timestamp(match["date"]).tz_localize("Europe/London").tz_convert("UTC") + pd.Timedelta(hours=15)
        upcoming = fixture_features(played, fixture_row(match["home"], match["away"], kickoff), BASE_ELO)
        pd.testing.assert_series_equal(upcoming[columns].astype(float), walk_forward.loc[index, columns].astype(float),
                                       check_names=False, rtol=1e-12)
