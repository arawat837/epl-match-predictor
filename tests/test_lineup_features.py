"""v2 lineup features follow docs/v2_lineup_plan.md section 5 exactly."""

import numpy as np
import pandas as pd
import pytest

from src.lineup_features import FEATURES, TeamMatch, build_lineup_features, match_features, regular_xi

DAY = pd.Timestamp("2024-08-01")


def team_match(n: int, xi: list[int] | None, keeper: int | None = None) -> TeamMatch:
    return TeamMatch(n, DAY + pd.Timedelta(weeks=n), None if xi is None else frozenset(xi),
                     keeper if keeper is not None else (xi[0] if xi else None), frozenset({90, 91}))


BASE = list(range(1, 12))


def test_regular_xi_needs_three_matches_with_lineups():
    assert regular_xi([team_match(0, BASE), team_match(1, BASE), team_match(2, None)]) is None
    assert regular_xi([team_match(0, BASE), team_match(1, BASE), team_match(2, BASE)]) == BASE


def test_regular_xi_ranks_by_starts_then_recency_then_lower_id():
    window = [team_match(0, BASE), team_match(1, [*BASE[:10], 20]), team_match(2, [*BASE[:10], 21]),
              team_match(3, [*BASE[:10], 30])]
    # players 1-10 start 4 times; 11, 20, 21, 30 once each: 30 started most recently
    assert regular_xi(window) == [*BASE[:10], 30]
    same_day = team_match(1, [*BASE[:10], 41]).date
    tie = [team_match(0, [*BASE[:10], 40]), team_match(1, [*BASE[:10], 41]),
           TeamMatch(2, same_day, frozenset([*BASE[:10], 42]), 1, frozenset())]
    # 40, 41 and 42 start once each; 41 and 42 most recently (same day), so the lower id wins
    assert regular_xi(tie)[-1] == 41


def test_features_for_a_match_with_three_earlier_lineups():
    history = [team_match(0, BASE), team_match(1, BASE), team_match(2, BASE),
               team_match(3, [*BASE[:9], 50, 51], keeper=1)]
    features = match_features(history, 3)
    assert features["xi_regulars"] == pytest.approx(9 / 11)
    assert features["xi_changes"] == 2.0 and features["keeper_changed"] == 0.0


def test_window_is_the_previous_ten_matches_only():
    history = [team_match(n, [*range(100, 111)]) for n in range(5)] + [team_match(n, BASE) for n in range(5, 15)]
    history.append(team_match(15, [*range(100, 111)]))
    assert match_features(history, 15)["xi_regulars"] == 0.0  # the 100s started only outside the window


def test_missing_xi_or_previous_lineup_gives_missing_values():
    assert all(np.isnan(value) for value in match_features([team_match(0, BASE), team_match(1, None)], 1).values())
    first = match_features([team_match(0, BASE)], 0)
    assert np.isnan(first["xi_changes"]) and np.isnan(first["keeper_changed"]) and np.isnan(first["xi_regulars"])
    after_gap = match_features([team_match(0, None), team_match(1, BASE)], 1)
    assert np.isnan(after_gap["xi_changes"])


def test_keeper_change_and_unknown_keeper():
    history = [team_match(0, BASE, keeper=1), team_match(1, [99, *BASE[1:]], keeper=99)]
    assert match_features(history, 1)["keeper_changed"] == 1.0
    unknown = [team_match(0, BASE, keeper=1), TeamMatch(1, DAY, frozenset(BASE), None, frozenset())]
    assert np.isnan(match_features(unknown, 1)["keeper_changed"])


def test_built_table_has_home_away_and_differences(seasons_with_promotion, lineups_with_promotion):
    features = build_lineup_features(seasons_with_promotion, lineups_with_promotion)
    assert features.index.equals(seasons_with_promotion.index)
    assert list(features.columns) == [f"{side}_{name}" for side in ("home", "away") for name in FEATURES] + \
        [f"{name}_diff" for name in FEATURES]
    pd.testing.assert_series_equal(features["xi_changes_diff"], features["home_xi_changes"] - features["away_xi_changes"],
                                   check_names=False)
    assert features.loc[features["home_xi_changes"].notna(), "home_xi_changes"].eq(1.0).mean() > 0.5


def test_a_new_spell_restarts_the_history(seasons_with_promotion, lineups_with_promotion):
    features = build_lineup_features(seasons_with_promotion, lineups_with_promotion)
    returning = seasons_with_promotion[(seasons_with_promotion["season"] == "2007-08")
                                       & ((seasons_with_promotion["home"] == "Team 19")
                                          | (seasons_with_promotion["away"] == "Team 19"))].index[0]
    side = "home" if seasons_with_promotion.loc[returning, "home"] == "Team 19" else "away"
    assert features.loc[returning, [f"{side}_xi_changes", f"{side}_xi_regulars", f"{side}_keeper_changed"]].isna().all()


def test_matches_without_lineups_get_missing_features(seasons_with_promotion, lineups_with_promotion):
    first_season = seasons_with_promotion.index[seasons_with_promotion["season"] == "2005-06"]
    features = build_lineup_features(seasons_with_promotion,
                                     lineups_with_promotion[~lineups_with_promotion["match"].isin(first_season)])
    assert features.loc[first_season].isna().all().all()
