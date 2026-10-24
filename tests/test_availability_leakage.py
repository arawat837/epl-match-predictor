"""Leakage tests for the availability values, in the style of tests/test_leakage.py.

For 50 random matches, the values are rebuilt from FPL rows and matches dated strictly
before the match, plus the match's own rows with every value replaced by an impossible
one (only who is listed survives, as the squad list as of that date). They must equal the
stored values. Planted leaks must make the same check fail.
"""

import random

import numpy as np
import pandas as pd
import pytest

import src.availability as availability
import src.availability_features as availability_features
from src.availability import History, build_availability, squad_list, unavailable_at_kickoff
from src.availability_features import build_availability_features
from src.fpl import FPL_DIR, load_fpl
from src.name_maps import link_rows, load_overrides, team_name_map
from src.splits import load_evaluation_matches
from scripts.audit_availability import AVAILABILITY_PATH
from scripts.evaluate_availability import FEATURES_PATH as STAGE8_PATH

pytestmark = pytest.mark.skipif(
    not (AVAILABILITY_PATH.exists() and FPL_DIR.exists()),
    reason="run `python -m scripts.audit_availability` first",
)

SAMPLE_SIZE = 50
PLANTED_SAMPLE = 10
SEED = 2026
IMPOSSIBLE = {"minutes": 9999, "yellow_cards": 9, "red_cards": 9, "bps": 999, "ict_index": 999.0, "price": 999.0}
LIST_COLUMNS = ["banned_red", "banned_yellow", "key_players"]


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return load_evaluation_matches()


@pytest.fixture(scope="module")
def linked(matches: pd.DataFrame) -> pd.DataFrame:
    rows = load_fpl()
    names = team_name_map(list(rows["fpl_team"].unique()), load_overrides())
    return link_rows(rows, matches, dict(zip(names["fpl_name"], names["canonical"])))


@pytest.fixture(scope="module")
def stored() -> pd.DataFrame:
    return pd.read_parquet(AVAILABILITY_PATH)


@pytest.fixture(scope="module")
def sample(stored: pd.DataFrame) -> list[int]:
    return random.Random(SEED).sample(list(stored.index), SAMPLE_SIZE)


def earlier_plus_scrambled(linked: pd.DataFrame, matches: pd.DataFrame, target: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rows and matches dated strictly before the target, plus the target with impossible values."""
    match = matches.loc[target]
    own = linked[(linked["date"] == match["date"]) & (linked["home"] == match["home"])
                 & (linked["away"] == match["away"])].assign(**IMPOSSIBLE)
    rows = pd.concat([linked[linked["date"] < match["date"]], own])
    return rows, pd.concat([matches[matches["date"] < match["date"]], matches.loc[[target]]])


def differing(rebuilt: pd.Series, expected: pd.Series) -> list[str]:
    """Columns whose rebuilt value differs from the expected one."""
    different = []
    for column, value in expected.items():
        got = rebuilt[column]
        if any(column.endswith(name) for name in LIST_COLUMNS):
            same = list(got) == list(value)
        elif isinstance(value, (int, float, np.number)) and not isinstance(value, bool):
            same = (pd.isna(got) and pd.isna(value)) or np.isclose(float(got), float(value), rtol=1e-9)
        else:
            same = got == value
        if not same:
            different.append(column)
    return different


def rebuild(linked: pd.DataFrame, matches: pd.DataFrame, target: int) -> pd.Series:
    rows, earlier = earlier_plus_scrambled(linked, matches, target)
    return build_availability(rows, earlier, only=[target]).loc[target]


@pytest.mark.parametrize("draw", range(SAMPLE_SIZE))
def test_values_use_only_earlier_rows_and_not_the_matchs_own(draw, linked, matches, stored, sample):
    target = sample[draw]
    assert differing(rebuild(linked, matches, target), stored.loc[target]) == []


def caught(linked: pd.DataFrame, matches: pd.DataFrame, targets: list[int]) -> int:
    """How many targets the leakage check flags, with the stored table built by the same code."""
    full = build_availability(linked, matches, only=targets)
    return sum(bool(differing(rebuild(linked, matches, target), full.loc[target])) for target in targets)


def own_match_included(schedule: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    return schedule[schedule["date"] <= date]


def every_snapshot(dates: np.ndarray, date: np.datetime64) -> int:
    return len(dates)


@pytest.mark.parametrize("patch", [("prior_matches", own_match_included), ("snapshot_cutoff", every_snapshot)],
                         ids=["match's own minutes", "snapshot dated after the match"])
def test_planted_leak_is_caught(patch, linked, matches, sample, monkeypatch):
    monkeypatch.setattr(availability, *patch)
    assert caught(linked, matches, sample[:PLANTED_SAMPLE]) >= PLANTED_SAMPLE // 2


def spells_unavailable_including_same_day(spells: pd.DataFrame, date: pd.Timestamp) -> set[object]:
    started = spells["start"] <= date
    return set(spells.loc[started & (spells["end"].isna() | (spells["end"] > date)), "player"])


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


def rebuild_stage8(linked: pd.DataFrame, matches: pd.DataFrame, target: int) -> pd.Series:
    rows, earlier = earlier_plus_scrambled(linked, matches, target)
    return build_availability_features(rows, earlier, only=[target]).loc[target]


@needs_stage8
@pytest.mark.parametrize("draw", range(SAMPLE_SIZE))
def test_stage8_features_use_only_earlier_rows_and_not_the_matchs_own(draw, linked, matches, stage8, stage8_sample):
    target = stage8_sample[draw]
    assert differing(rebuild_stage8(linked, matches, target), stage8.loc[target]) == []


def caught_stage8(linked: pd.DataFrame, matches: pd.DataFrame, targets: list[int]) -> int:
    full = build_availability_features(linked, matches, only=targets)
    return sum(bool(differing(rebuild_stage8(linked, matches, target), full.loc[target])) for target in targets)


def absence_from_this_match(prior: pd.DataFrame, date: pd.Timestamp) -> pd.Timestamp:
    return date


@needs_stage8
@pytest.mark.parametrize("module, patch", [(availability_features, ("absence_match_date", absence_from_this_match)),
                                           (availability, ("snapshot_cutoff", every_snapshot))],
                         ids=["recent_absence from match t's own minutes", "squad value snapshot after the match"])
def test_stage8_planted_leak_is_caught(module, patch, linked, matches, stage8, monkeypatch):
    with_absence = stage8.index[stage8["home_recent_absence"].notna() & stage8["away_recent_absence"].notna()]
    targets = random.Random(SEED).sample(list(with_absence), PLANTED_SAMPLE)
    monkeypatch.setattr(module, *patch)
    assert caught_stage8(linked, matches, targets) >= PLANTED_SAMPLE // 2


@pytest.mark.parametrize("rule, leaks", [(unavailable_at_kickoff, False), (spells_unavailable_including_same_day, True)],
                         ids=["started before the match date", "planted: starts on the match date"])
def test_injury_spells_are_checked_against_spells_started_before_the_match(rule, leaks):
    day = pd.Timestamp("2021-03-13")
    spells = pd.DataFrame({"player": ["knock in training", "injured in this match"],
                           "start": [pd.Timestamp("2021-03-01"), day], "end": [pd.NaT, pd.NaT]})
    earlier = spells[spells["start"] < day]
    assert (rule(spells, day) != rule(earlier, day)) is leaks
