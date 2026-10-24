"""Leakage tests for the availability values, in the style of tests/test_leakage.py.

For 50 random matches, the values are rebuilt from FPL rows and matches dated strictly
before the match, plus the match's own rows with every value replaced by an impossible
one (only who is listed survives, as the squad list as of that date). They must equal the
stored values. Planted leaks must make the same check fail.
"""

import random

import pandas as pd
import pytest

import src.availability as availability
import src.availability_features as availability_features
from src.availability import History, squad_list, unavailable_at_kickoff
from src.fpl import FPL_DIR
from src.leak_checks import (absence_from_this_match, differing, every_snapshot, flagged_availability, flagged_stage8,
                             linked_fpl_rows, own_match_included, rebuild_availability, rebuild_stage8,
                             spells_unavailable_including_same_day)
from src.leak_samples import PLANTED_SAMPLE, SAMPLE_SIZE, SEED
from src.splits import load_evaluation_matches
from scripts.audit_availability import AVAILABILITY_PATH
from scripts.evaluate_availability import FEATURES_PATH as STAGE8_PATH

pytestmark = pytest.mark.skipif(
    not (AVAILABILITY_PATH.exists() and FPL_DIR.exists()),
    reason="run `python -m scripts.audit_availability` first",
)


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return load_evaluation_matches()


@pytest.fixture(scope="module")
def linked(matches: pd.DataFrame) -> pd.DataFrame:
    return linked_fpl_rows(matches)


@pytest.fixture(scope="module")
def stored() -> pd.DataFrame:
    return pd.read_parquet(AVAILABILITY_PATH)


@pytest.fixture(scope="module")
def sample(stored: pd.DataFrame) -> list[int]:
    return random.Random(SEED).sample(list(stored.index), SAMPLE_SIZE)


@pytest.mark.parametrize("draw", range(SAMPLE_SIZE))
def test_values_use_only_earlier_rows_and_not_the_matchs_own(draw, linked, matches, stored, sample):
    target = sample[draw]
    assert differing(rebuild_availability(linked, matches, target), stored.loc[target]) == []


@pytest.mark.parametrize("patch", [("prior_matches", own_match_included), ("snapshot_cutoff", every_snapshot)],
                         ids=["match's own minutes", "snapshot dated after the match"])
def test_planted_leak_is_caught(patch, linked, matches, sample, monkeypatch):
    monkeypatch.setattr(availability, *patch)
    assert flagged_availability(linked, matches, sample[:PLANTED_SAMPLE]) >= PLANTED_SAMPLE // 2


def test_scrambling_the_matchs_own_minutes_leaves_its_squad_list_unchanged(linked, matches, sample):
    original = History.build(linked, matches)
    for target in sample[:PLANTED_SAMPLE]:
        match = matches.loc[target]
        own = (linked["date"] == match["date"]) & (linked["home"] == match["home"]) & (linked["away"] == match["away"])
        scrambled = History.build(linked.assign(minutes=linked["minutes"].where(~own, 9999)), matches)
        for side in ("home", "away"):
            assert squad_list(scrambled, match[side], match["date"]) == squad_list(original, match[side], match["date"])


needs_stage8 = pytest.mark.skipif(not STAGE8_PATH.exists(), reason="run `python -m scripts.evaluate_availability` first")


@pytest.fixture(scope="module")
def stage8() -> pd.DataFrame:
    return pd.read_parquet(STAGE8_PATH)


@pytest.fixture(scope="module")
def stage8_sample(stage8: pd.DataFrame) -> list[int]:
    return random.Random(SEED).sample(list(stage8.index), SAMPLE_SIZE)


@needs_stage8
@pytest.mark.parametrize("draw", range(SAMPLE_SIZE))
def test_stage8_features_use_only_earlier_rows_and_not_the_matchs_own(draw, linked, matches, stage8, stage8_sample):
    target = stage8_sample[draw]
    assert differing(rebuild_stage8(linked, matches, target), stage8.loc[target]) == []


@needs_stage8
@pytest.mark.parametrize("module, patch", [(availability_features, ("absence_match_date", absence_from_this_match)),
                                           (availability, ("snapshot_cutoff", every_snapshot))],
                         ids=["recent_absence from match t's own minutes", "squad value snapshot after the match"])
def test_stage8_planted_leak_is_caught(module, patch, linked, matches, stage8, monkeypatch):
    with_absence = stage8.index[stage8["home_recent_absence"].notna() & stage8["away_recent_absence"].notna()]
    targets = random.Random(SEED).sample(list(with_absence), PLANTED_SAMPLE)
    monkeypatch.setattr(module, *patch)
    assert flagged_stage8(linked, matches, targets) >= PLANTED_SAMPLE // 2


@pytest.mark.parametrize("rule, leaks", [(unavailable_at_kickoff, False), (spells_unavailable_including_same_day, True)],
                         ids=["started before the match date", "planted: starts on the match date"])
def test_injury_spells_are_checked_against_spells_started_before_the_match(rule, leaks):
    day = pd.Timestamp("2021-03-13")
    spells = pd.DataFrame({"player": ["knock in training", "injured in this match"],
                           "start": [pd.Timestamp("2021-03-01"), day], "end": [pd.NaT, pd.NaT]})
    earlier = spells[spells["start"] < day]
    assert (rule(spells, day) != rule(earlier, day)) is leaks
