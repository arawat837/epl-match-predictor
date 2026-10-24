"""Gate L leakage checks for the v2 lineup features (docs/v2_lineup_plan.md section 7).

A match's features are rebuilt from the matches dated strictly before it plus that match alone:
its announced XI is kept (allowed under the v2 prediction-time rule), its bench is replaced by
impossible player ids, its result and stats are scrambled, and other matches on the same day are
left out. The rebuilt features must equal those built from the full table. For a planted leak the
leaky code builds both, as in src/leak_checks.py.

Samples (all among matches with both lineups): a random one, a stratified one for the real-code
rebuild, and for each planted leak a sample targeted at where it first shows. A side's lineup
position is how many earlier matches in its spell have lineups.
"""

import pandas as pd

import src.lineup_features as lineup_features
from src.leak_checks import earlier_plus_scrambled, features_differ, planted
from src.leak_samples import (PER_STRATUM, PLANTED_SAMPLE, SAMPLE_SIZE, matches_where, random_sample, shuffled,
                              side_positions, stratified_from)
from src.lineup_features import TeamMatch, build_lineup_features, team_histories

IMPOSSIBLE_PLAYER = -1  # bench ids become -1, -2, ...; API player ids are positive


def lineup_matches(lineups: pd.DataFrame) -> list[int]:
    """Matches where both sides have a lineup."""
    sides = lineups.groupby("match")["side"].nunique()
    return sorted(sides.index[sides == 2])


def earlier_plus_own(matches: pd.DataFrame, lineups: pd.DataFrame, target: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Matches and lineups dated strictly before the target, plus the target with its result and
    stats scrambled and its bench replaced by impossible ids (its XI kept)."""
    rebuilt_matches = earlier_plus_scrambled(matches, target)
    kept = lineups["match"].isin(rebuilt_matches.index)
    own_bench = (lineups["match"] == target) & ~lineups["starter"]
    rebuilt_lineups = lineups[kept].copy()
    bench_ids = range(IMPOSSIBLE_PLAYER, IMPOSSIBLE_PLAYER - int(own_bench.sum()), -1)
    rebuilt_lineups.loc[own_bench[kept], "player_id"] = list(bench_ids)
    return rebuilt_matches, rebuilt_lineups


def random_matches(population: list[int], size: int) -> list[int]:
    """Seeded random matches; the Stage 4 draw when there are enough to draw 50 from."""
    return random_sample(population, size) if len(population) >= SAMPLE_SIZE else shuffled(population)[:size]


def flagged(matches: pd.DataFrame, lineups: pd.DataFrame, full: pd.DataFrame, targets: list[int]) -> int:
    """How many targets' rebuilt features differ from `full` (built by the same code)."""
    return sum(features_differ(build_lineup_features(*earlier_plus_own(matches, lineups, target)).loc[target],
                               full.loc[target]) for target in targets)


# ---------- planted leaks ----------

def bench_as_starters(team_match: TeamMatch) -> frozenset[int]:
    """PLANTED LEAK: the match's bench counted as starting (the rule allows the XI only)."""
    return team_match.xi | team_match.bench


def next_match(history: list[TeamMatch], position: int) -> TeamMatch | None:
    """PLANTED LEAK: the 'previous' XI read from the team's next match."""
    return history[position + 1] if position + 1 < len(history) else None


def later_window(history: list[TeamMatch], position: int) -> list[TeamMatch]:
    """PLANTED LEAK: the regular XI built from the team's next 10 matches."""
    return history[position + 1:position + 1 + lineup_features.WINDOW]


FIRST_LINEUP = "a side's first match with lineup data"
EARLY_LINEUPS = "a side's 2nd or 3rd match with lineup data"
SETTLED_LINEUPS = "a side's 4th or later match with lineup data"
LINEUP_LEAKS = [  # (check, function replaced in src.lineup_features, leaky version, targeted sample)
    ("the match's own bench counted as starters", "starters", bench_as_starters, SETTLED_LINEUPS),
    ("previous XI read from the next match", "previous_match", next_match, FIRST_LINEUP),
    ("regular XI built from later matches", "window_matches", later_window, EARLY_LINEUPS),
]


def lineup_positions(matches: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    """Per team match with a lineup: how many earlier matches in its spell have lineups."""
    rows = []
    for spell in team_histories(matches, lineups).values():
        seen = 0
        for _, team_match in spell:
            if team_match.xi is not None:
                rows.append({"match": team_match.match, "lineup_position": seen})
                seen += 1
    return pd.DataFrame(rows, columns=["match", "lineup_position"])


def lineup_strata(matches: pd.DataFrame, lineups: pd.DataFrame) -> dict[str, list[int]]:
    """Matches with both lineups where either side is in each case."""
    both = set(lineup_matches(lineups))
    positions = lineup_positions(matches, lineups)
    sides = side_positions(matches)

    def where(mask: pd.Series) -> list[int]:
        return sorted(both.intersection(positions.loc[mask, "match"]))

    return {FIRST_LINEUP: where(positions["lineup_position"] == 0),
            EARLY_LINEUPS: where(positions["lineup_position"].between(1, 2)),
            SETTLED_LINEUPS: where(positions["lineup_position"] >= 3),
            "first match of a season": sorted(both.intersection(matches_where(sides, lambda p: p["season_match"] == 1))),
            "promoted side's first 5 matches": sorted(both.intersection(
                matches_where(sides, lambda p: p["promoted"] & (p["season_match"] <= 5))))}


def rebuild_sample(matches: pd.DataFrame, lineups: pd.DataFrame, size: int = SAMPLE_SIZE) -> list[int]:
    """The real-code rebuild sample: at least PER_STRATUM matches from every lineup stratum."""
    return stratified_from(lineup_strata(matches, lineups).values(), lineup_matches(lineups), size, PER_STRATUM)


def real_code_flags(report: pd.DataFrame) -> int:
    """Matches flagged on the real code in a lineup check report (should be 0)."""
    real = report["check"].str.startswith("real code")
    return int(report.loc[real, "targeted_flagged"].sum() + report["real_code_targeted_flagged"].sum())


def lineup_check_report(matches: pd.DataFrame, lineups: pd.DataFrame, limit: int | None = None) -> pd.DataFrame:
    """Gate L counts: the real-code rebuild on the stratified sample, then each planted leak on a
    random and a targeted sample with the real code on that targeted sample. `limit` keeps only the
    first matches of every sample."""
    def capped(sample: list[int]) -> list[int]:
        return sample if limit is None else sample[:limit]

    both, strata = lineup_matches(lineups), lineup_strata(matches, lineups)
    real = build_lineup_features(matches, lineups)
    stratified = capped(rebuild_sample(matches, lineups))
    rows = [{"check": "real code: rebuilt from earlier lineups plus the match's own XI", "random_cases": None,
             "random_flagged": None, "targeted_sample": "stratified", "targeted_cases": len(stratified),
             "targeted_flagged": flagged(matches, lineups, real, stratified)}]
    at_random = capped(random_matches(both, PLANTED_SAMPLE))
    for check, name, leaky, target in LINEUP_LEAKS:
        targeted = capped(shuffled(strata[target])[:PLANTED_SAMPLE])
        real_flags = flagged(matches, lineups, real, targeted)
        with planted(lineup_features, name, leaky):
            full = build_lineup_features(matches, lineups)
            rows.append({"check": check, "random_cases": len(at_random),
                         "random_flagged": flagged(matches, lineups, full, at_random), "targeted_sample": target,
                         "targeted_cases": len(targeted), "targeted_flagged": flagged(matches, lineups, full, targeted),
                         "real_code_targeted_flagged": real_flags})
    return pd.DataFrame(rows).astype({column: "Int64" for column in
                                      ["random_cases", "random_flagged", "targeted_cases", "targeted_flagged",
                                       "real_code_targeted_flagged"]})
