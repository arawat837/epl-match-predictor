"""Gate L leakage checks for the lineup features: planted leaks are caught where they show, the real
code is not flagged, and the rebuild keeps only what the v2 rule allows."""

import pandas as pd
import pytest

import src.lineup_features as lineup_features
from src.leak_checks import planted
from src.lineup_features import build_lineup_features
from src.lineup_leaks import (LINEUP_LEAKS, earlier_plus_own, flagged, lineup_check_report, lineup_matches,
                              lineup_strata, real_code_flags, rebuild_sample)


def test_rebuild_keeps_the_own_xi_scrambles_the_own_bench_and_drops_same_day_matches(seasons_with_promotion,
                                                                                    lineups_with_promotion):
    target = seasons_with_promotion.index[100]
    matches, lineups = earlier_plus_own(seasons_with_promotion, lineups_with_promotion, target)
    day = seasons_with_promotion.loc[target, "date"]
    assert not ((matches["date"] == day) & (matches.index != target)).any()
    own, original = lineups[lineups["match"] == target], lineups_with_promotion[lineups_with_promotion["match"] == target]
    assert set(own.loc[own["starter"], "player_id"]) == set(original.loc[original["starter"], "player_id"])
    assert (own.loc[~own["starter"], "player_id"] < 0).all() and own.loc[~own["starter"], "player_id"].is_unique
    assert matches.loc[target, "result"] != seasons_with_promotion.loc[target, "result"]


def test_strata_and_rebuild_sample_hold_only_matches_with_both_lineups(seasons_with_promotion, lineups_with_promotion):
    both = set(lineup_matches(lineups_with_promotion))
    strata = lineup_strata(seasons_with_promotion, lineups_with_promotion)
    assert all(set(members) <= both and members for members in strata.values())
    sample = rebuild_sample(seasons_with_promotion, lineups_with_promotion, size=20)
    assert len(sample) == len(set(sample)) == 20 and set(sample) <= both


@pytest.mark.parametrize("check, name, leaky, target", LINEUP_LEAKS, ids=[leak[0] for leak in LINEUP_LEAKS])
def test_planted_leak_is_flagged_on_its_targeted_case_and_the_real_code_is_not(check, name, leaky, target,
                                                                                 seasons_with_promotion,
                                                                                 lineups_with_promotion):
    targets = lineup_strata(seasons_with_promotion, lineups_with_promotion)[target][:3]
    real = build_lineup_features(seasons_with_promotion, lineups_with_promotion)
    assert flagged(seasons_with_promotion, lineups_with_promotion, real, targets) == 0
    with planted(lineup_features, name, leaky):
        full = build_lineup_features(seasons_with_promotion, lineups_with_promotion)
        assert flagged(seasons_with_promotion, lineups_with_promotion, full, targets) == len(targets)


def test_report_counts_real_code_flags():
    report = pd.DataFrame({"check": ["real code: rebuilt", "leak"], "targeted_flagged": [1, 9],
                           "real_code_targeted_flagged": pd.array([None, 2], dtype="Int64")})
    assert real_code_flags(report) == 3


def test_small_report_on_synthetic_seasons_flags_no_real_code(seasons_with_promotion, lineups_with_promotion):
    report = lineup_check_report(seasons_with_promotion, lineups_with_promotion, limit=2)
    assert real_code_flags(report) == 0
    assert (report.loc[1:, "targeted_flagged"] == report.loc[1:, "targeted_cases"]).all()


CACHED_SEASONS = [2024, 2023, 2022]


@pytest.fixture(scope="module")
def cached() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Real matches, linked cached fixtures and their lineups (skips if the cache is too small)."""
    from src.config import MATCHES_PATH
    from src.lineups import link_fixtures, load_fixtures, load_lineups, match_lineups
    from src.splits import load_evaluation_matches

    if not MATCHES_PATH.exists():
        pytest.skip("run `python -m scripts.build_dataset` first")
    matches = load_evaluation_matches()
    linked = link_fixtures(load_fixtures(CACHED_SEASONS), matches)
    rows = match_lineups(load_lineups(linked["fixture_id"])[0], linked)
    if len(lineup_matches(rows)) < 30:
        pytest.skip("run `python -m scripts.fetch_lineups` first (needs 30 cached lineups)")
    return matches, linked, rows


def test_cached_fixtures_link_to_matches(cached):
    from src.lineups import LINK_THRESHOLD, link_rate

    assert link_rate(cached[1]) >= LINK_THRESHOLD


def test_small_rerun_on_cached_lineups_flags_no_real_code(cached):
    matches, _, rows = cached
    report = lineup_check_report(matches, rows, limit=2)
    assert real_code_flags(report) == 0
