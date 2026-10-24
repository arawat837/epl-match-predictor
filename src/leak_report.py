"""reports/planted_leaks.csv: what each leakage check flags, on the real code and on planted leaks.

Every planted leak is checked on a random sample and on a sample targeted at the rare case
where it first shows, and the real code is checked on that same targeted sample. A leak that
only shows in rare cases can pass a random sample; the targeted column shows whether the
check would still catch it. All samples are seeded; `limit` keeps only the first matches of
each, so a smaller run checks a prefix of the full one.
"""

from collections.abc import Callable
from pathlib import Path

import pandas as pd

import src.availability as availability
import src.availability_features as availability_features
import src.features as features
from src.availability import unavailable_at_kickoff
from src.config import FEATURES_PATH
from src.features import build_features
from src.leak_checks import (absence_from_this_match, differing, every_snapshot, flagged_availability, flagged_features,
                             flagged_stage8, linked_fpl_rows, own_match_included, planted, post_update_elo,
                             rebuild_availability, rebuild_stage8, rest_until_next_match,
                             season_ppg_including_this_match, spells_from_gap_to_next_match,
                             spells_unavailable_including_same_day, stored_like, unshifted_rolling_mean)
from src.leak_samples import PLANTED_SAMPLE, random_sample, stratified_sample, targeted_sample
from src.splits import load_evaluation_matches

COLUMNS = ["stage", "check", "random_cases", "random_flagged", "targeted_sample", "targeted_cases",
           "targeted_flagged", "real_code_targeted_flagged"]
COUNTS = ["random_cases", "random_flagged", "targeted_cases", "targeted_flagged", "real_code_targeted_flagged"]
STRATIFIED = "stratified: season openers, first 3 matchweeks, promoted sides' first 5, after a 200-day gap"
CHECK_EVERY_CASE = {"last match before a missed season"}  # rare enough to check all of them

STAGE4_LEAKS = [  # (check, function replaced in src.features, leaky version, targeted sample)
    ("rolling window without shift(1)", "rolling_mean", unshifted_rolling_mean, "third match of a spell"),
    ("days rest measured to the next match", "days_rest", rest_until_next_match, "first match of a spell"),
    ("season PPG includes this match", "season_ppg", season_ppg_including_this_match, "first match of a season"),
    ("Elo stores post-update ratings", "pre_match_elo", post_update_elo, "first match of a season"),
    ("spell break read from the next match", "spells", spells_from_gap_to_next_match,
     "last match before a missed season"),
]
STAGE7_TARGET = "first match of a season"
STAGE7_LEAKS = [  # (check, module, function replaced, leaky version)
    ("key players include the match's own minutes", availability, "prior_matches", own_match_included),
    ("price snapshot dated after the match", availability, "snapshot_cutoff", every_snapshot),
]
STAGE8_TARGET = "both sides' recent_absence defined"
STAGE8_LEAKS = [
    ("recent_absence from match t's own minutes", availability_features, "absence_match_date", absence_from_this_match),
    ("squad value from a snapshot dated after the match", availability, "snapshot_cutoff", every_snapshot),
]


def capped(sample: list, limit: int | None) -> list:
    return sample if limit is None else sample[:limit]


def result(stage: str, check: str, at_random: list | None, random_flagged: int | None, target: str | None,
           targeted: list | None, targeted_flagged: int | None, real_flagged: int | None) -> dict[str, object]:
    return {"stage": stage, "check": check, "random_cases": None if at_random is None else len(at_random),
            "random_flagged": random_flagged, "targeted_sample": target,
            "targeted_cases": None if targeted is None else len(targeted),
            "targeted_flagged": targeted_flagged, "real_code_targeted_flagged": real_flagged}


def stage4_rows(matches: pd.DataFrame, stored: pd.DataFrame, limit: int | None) -> list[dict[str, object]]:
    stage, stored = "4 features", stored_like(matches, stored)
    random50, stratified = capped(random_sample(matches.index), limit), capped(stratified_sample(matches), limit)
    real_stratified = flagged_features(matches, stored, stratified)
    rows = [result(stage, "real code: rebuilt from earlier rows, own stats scrambled", random50,
                   flagged_features(matches, stored, random50), STRATIFIED, stratified, real_stratified, real_stratified)]
    random10, real, real_flags = capped(random_sample(matches.index, PLANTED_SAMPLE), limit), build_features(matches), {}
    for check, name, leaky, target in STAGE4_LEAKS:
        size = None if target in CHECK_EVERY_CASE else PLANTED_SAMPLE
        targeted = capped(targeted_sample(matches, target, size), limit)
        if target not in real_flags:
            real_flags[target] = flagged_features(matches, real, targeted)
        with planted(features, name, leaky):
            full = build_features(matches)
            rows.append(result(stage, check, random10, flagged_features(matches, full, random10), target, targeted,
                               flagged_features(matches, full, targeted), real_flags[target]))
    return rows


def stage7_rows(linked: pd.DataFrame, matches: pd.DataFrame, stored: pd.DataFrame,
                limit: int | None) -> list[dict[str, object]]:
    stage, random50 = "7 availability", capped(random_sample(stored.index), limit)
    rebuilt = sum(bool(differing(rebuild_availability(linked, matches, target), stored.loc[target])) for target in random50)
    rows = [result(stage, "real code: rebuilt from earlier rows, own rows scrambled", random50, rebuilt,
                   None, None, None, None)]
    random10 = capped(random_sample(stored.index, PLANTED_SAMPLE), limit)
    targeted = capped(targeted_sample(matches, STAGE7_TARGET, within=stored.index), limit)
    real_targeted = flagged_availability(linked, matches, targeted)
    for check, module, name, leaky in STAGE7_LEAKS:
        with planted(module, name, leaky):
            rows.append(result(stage, check, random10, flagged_availability(linked, matches, random10), STAGE7_TARGET,
                               targeted, flagged_availability(linked, matches, targeted), real_targeted))
    return rows


def injury_rule_row() -> dict[str, object]:
    """The spell rule on two synthetic spells, one started before the match date and one on it."""
    day = pd.Timestamp("2021-03-13")
    spells = pd.DataFrame({"player": ["knock in training", "injured in this match"],
                           "start": [pd.Timestamp("2021-03-01"), day], "end": [pd.NaT, pd.NaT]})
    earlier = spells[spells["start"] < day]

    def flags(rule: Callable[[pd.DataFrame, pd.Timestamp], set[object]]) -> int:
        return int(rule(spells, day) != rule(earlier, day))

    return result("7 availability", "injury spell starting on the match date counted", None, None,
                  "synthetic spells: one started before the match date, one on it", [day],
                  flags(spells_unavailable_including_same_day), flags(unavailable_at_kickoff))


def stage8_rows(linked: pd.DataFrame, matches: pd.DataFrame, stored: pd.DataFrame,
                limit: int | None) -> list[dict[str, object]]:
    stage, random50 = "8 features", capped(random_sample(stored.index), limit)
    rebuilt = sum(bool(differing(rebuild_stage8(linked, matches, target), stored.loc[target])) for target in random50)
    rows = [result(stage, "real code: rebuilt from earlier rows, own rows scrambled", random50, rebuilt,
                   None, None, None, None)]
    random10 = capped(random_sample(stored.index, PLANTED_SAMPLE), limit)
    with_absence = stored.index[stored["home_recent_absence"].notna() & stored["away_recent_absence"].notna()]
    targeted = capped(random_sample(with_absence, PLANTED_SAMPLE), limit)
    real_targeted = flagged_stage8(linked, matches, targeted)
    for check, module, name, leaky in STAGE8_LEAKS:
        with planted(module, name, leaky):
            rows.append(result(stage, check, random10, flagged_stage8(linked, matches, random10), STAGE8_TARGET,
                               targeted, flagged_stage8(linked, matches, targeted), real_targeted))
    return rows


def planted_leak_report(availability_path: Path, stage8_path: Path, limit: int | None = None,
                        features_path: Path = FEATURES_PATH) -> pd.DataFrame:
    """Every check's counts, one row per check (see the module docstring)."""
    matches = load_evaluation_matches()
    linked = linked_fpl_rows(matches)
    rows = [*stage4_rows(matches, pd.read_parquet(features_path), limit),
            *stage7_rows(linked, matches, pd.read_parquet(availability_path), limit), injury_rule_row(),
            *stage8_rows(linked, matches, pd.read_parquet(stage8_path), limit)]
    return pd.DataFrame(rows, columns=COLUMNS).astype({column: "Int64" for column in COUNTS})


def real_code_flags(report: pd.DataFrame) -> int:
    """Matches flagged on the real code anywhere in the report (should be 0)."""
    real = report["check"].str.startswith("real code")
    return int(report.loc[real, "random_flagged"].sum() + report["real_code_targeted_flagged"].sum())
