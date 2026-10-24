"""Samples for the leakage checks, on synthetic seasons with a promotion and a missed season."""

import pandas as pd

from src.leak_samples import (STRATA, matches_where, random_sample, side_positions, stratified_sample,
                              targeted_sample)


def positions_of(positions: pd.DataFrame, team: str) -> pd.DataFrame:
    return positions[positions["team"] == team].reset_index(drop=True)


def test_positions_count_matches_in_the_season_and_the_spell(seasons_with_promotion):
    team19 = positions_of(side_positions(seasons_with_promotion), "Team 19")
    assert team19["season_match"].tolist() == [*range(1, 39), *range(1, 39)]
    assert team19["spell_match"].tolist() == [*range(1, 39), *range(1, 39)]  # the missed season breaks the spell
    team00 = positions_of(side_positions(seasons_with_promotion), "Team 00")
    assert team00["spell_match"].tolist() == list(range(1, 3 * 38 + 1))  # summer breaks keep it


def test_promoted_sides_are_those_missing_from_the_previous_season(seasons_with_promotion):
    positions = side_positions(seasons_with_promotion)
    promoted = positions[positions["promoted"]].groupby("team")["season"].agg(set)
    assert promoted.to_dict() == {"Team 19": {"2007-08"}, "Team 20": {"2006-07"}}  # never in the first season


def test_gaps_mark_the_matches_either_side_of_a_missed_season(seasons_with_promotion):
    team19 = positions_of(side_positions(seasons_with_promotion), "Team 19")
    assert team19.index[team19["gap_after"] > 200].tolist() == [37]
    assert team19.index[team19["gap_before"] > 200].tolist() == [38]


def test_stratified_sample_holds_every_rare_case_and_fills_the_rest_at_random(seasons_with_promotion):
    sample = stratified_sample(seasons_with_promotion, size=30, per_stratum=3)
    positions = side_positions(seasons_with_promotion)
    assert len(sample) == len(set(sample)) == 30
    for condition in STRATA.values():
        members = set(matches_where(positions, condition))
        assert len(members.intersection(sample)) >= min(3, len(members))
    assert sample == stratified_sample(seasons_with_promotion, size=30, per_stratum=3)


def test_a_stratum_smaller_than_asked_is_taken_whole(seasons_with_promotion):
    after_gap = matches_where(side_positions(seasons_with_promotion), STRATA["after a gap of over 200 days"])
    assert len(after_gap) == 1
    assert set(after_gap) <= set(stratified_sample(seasons_with_promotion, size=30, per_stratum=3))


def test_targeted_samples_hold_only_their_case(seasons_with_promotion):
    before_gap = targeted_sample(seasons_with_promotion, "last match before a missed season", size=None)
    match = seasons_with_promotion.loc[before_gap[0]]
    assert len(before_gap) == 1 and "Team 19" in (match["home"], match["away"]) and match["season"] == "2005-06"
    openers = targeted_sample(seasons_with_promotion, "first match of a season", size=4)
    assert len(openers) == 4
    assert set(openers) <= set(matches_where(side_positions(seasons_with_promotion), lambda p: p["season_match"] == 1))


def test_targeted_samples_can_be_limited_to_rows_with_data(seasons_with_promotion):
    within = list(seasons_with_promotion.index[seasons_with_promotion["season"] == "2007-08"])
    sample = targeted_sample(seasons_with_promotion, "first match of a season", size=None, within=within)
    assert len(sample) == 10 and set(sample) <= set(within)


def test_smaller_random_samples_are_prefixes_of_larger_ones(seasons_with_promotion):
    index = seasons_with_promotion.index
    assert random_sample(index, 10) == random_sample(index, 50)[:10]
