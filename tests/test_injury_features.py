"""v2-pre injury features (plan amendment A2) and their leakage checks, on synthetic seasons."""

import numpy as np
import pandas as pd
import pytest

import src.injury_features as injury_features
from src.injury_features import build_injury_features
from src.injury_leaks import (INJURY_LEAKS, earlier_plus_own_list, flagged, injury_check_report, injury_targets,
                              real_code_flags)
from src.leak_checks import planted

COVERED = {"2005-06", "2006-07", "2007-08"}


def team_number(name: str) -> int:
    return int(name.split()[-1])


@pytest.fixture
def injuries(seasons_with_promotion: pd.DataFrame) -> pd.DataFrame:
    """For every 5th match: the home side lists its ever-present player 13 and its never-starting
    player 16 as missing, and player 2 as doubtful."""
    rows = []
    for match in seasons_with_promotion.index[::5]:
        team = team_number(seasons_with_promotion.at[match, "home"])
        rows += [{"match": match, "side": "home", "player_id": team * 100 + player, "type": kind}
                 for player, kind in ((13, "Missing Fixture"), (16, "Missing Fixture"), (2, "Questionable"))]
    return pd.DataFrame(rows)


def test_listed_regulars_and_count(seasons_with_promotion, lineups_with_promotion, injuries):
    features = build_injury_features(seasons_with_promotion, lineups_with_promotion, injuries, COVERED)
    listed = seasons_with_promotion.index[::5]
    late = [match for match in listed if seasons_with_promotion.at[match, "season"] == "2006-07"]
    assert (features.loc[late, "home_injured_count"] == 2.0).all()  # the doubtful player is not counted
    assert features.loc[late, "home_injured_regulars"].eq(1 / 11).all()  # only player 13 is a regular
    unlisted = seasons_with_promotion.index.difference(listed)
    assert (features.loc[unlisted, "home_injured_count"] == 0.0).all()


def test_uncovered_seasons_are_missing(seasons_with_promotion, lineups_with_promotion, injuries):
    features = build_injury_features(seasons_with_promotion, lineups_with_promotion, injuries, {"2006-07"})
    first = seasons_with_promotion.index[seasons_with_promotion["season"] == "2005-06"]
    assert features.loc[first].isna().all().all()


def test_the_matchs_own_xi_does_not_change_its_features(seasons_with_promotion, lineups_with_promotion, injuries):
    target = seasons_with_promotion.index[500]
    without_own = lineups_with_promotion[lineups_with_promotion["match"] != target]
    full = build_injury_features(seasons_with_promotion, lineups_with_promotion, injuries, COVERED)
    rebuilt = build_injury_features(seasons_with_promotion, without_own, injuries, COVERED)
    pd.testing.assert_series_equal(full.loc[target], rebuilt.loc[target])


def test_rebuild_keeps_only_earlier_data_and_the_fixtures_own_list(seasons_with_promotion, lineups_with_promotion,
                                                                   injuries):
    target = seasons_with_promotion.index[500]
    matches, lineups, listed = earlier_plus_own_list(seasons_with_promotion, lineups_with_promotion, injuries, target)
    assert target not in set(lineups["match"])
    assert set(listed["match"]) <= set(matches.index) and target in set(matches.index)


@pytest.mark.parametrize("check, name, leaky, target", INJURY_LEAKS, ids=[leak[0] for leak in INJURY_LEAKS])
def test_planted_leak_is_flagged_on_its_targeted_case_and_the_real_code_is_not(check, name, leaky, target,
                                                                                 seasons_with_promotion,
                                                                                 lineups_with_promotion, injuries):
    targets = injury_targets(seasons_with_promotion, lineups_with_promotion, injuries, COVERED)[target][:3]
    real = build_injury_features(seasons_with_promotion, lineups_with_promotion, injuries, COVERED)
    assert len(targets) == 3
    assert flagged(seasons_with_promotion, lineups_with_promotion, injuries, COVERED, real, targets) == 0
    with planted(injury_features, name, leaky):
        full = build_injury_features(seasons_with_promotion, lineups_with_promotion, injuries, COVERED)
        assert flagged(seasons_with_promotion, lineups_with_promotion, injuries, COVERED, full, targets) == 3


def test_small_report_flags_no_real_code(seasons_with_promotion, lineups_with_promotion, injuries):
    report = injury_check_report(seasons_with_promotion, lineups_with_promotion, injuries, COVERED, limit=2)
    assert real_code_flags(report) == 0
    assert (report.loc[1:, "targeted_flagged"] == report.loc[1:, "targeted_cases"]).all()
    assert not np.isnan(report.loc[0, "random_flagged"])
