"""Which matches the leakage checks test: random, stratified and targeted samples.

Positions (a side's match number in the season and in its spell, promoted or not, the gaps
before and after) are read from the whole match table, later matches included. They only
choose which matches to check; they never feed a feature.
"""

import random
from collections.abc import Callable, Iterable, Sequence

import pandas as pd

from src.features import NEW_SPELL_GAP_DAYS, long_table

SEED = 2026
SAMPLE_SIZE = 50
PER_STRATUM = 5
PLANTED_SAMPLE = 10

Condition = Callable[[pd.DataFrame], pd.Series]

# Rare cases every stratified sample includes: a match qualifies if either side does.
STRATA: dict[str, Condition] = {
    "first match of a season": lambda p: p["season_match"] == 1,
    "first 3 matchweeks": lambda p: p["season_match"] <= 3,
    "promoted side's first 5 matches": lambda p: p["promoted"] & (p["season_match"] <= 5),
    "after a gap of over 200 days": lambda p: p["gap_before"] > NEW_SPELL_GAP_DAYS,
}

# Where each planted leak first shows: the targeted samples of reports/planted_leaks.csv.
TARGETS: dict[str, Condition] = {
    "third match of a spell": lambda p: p["spell_match"] == 3,
    "first match of a spell": lambda p: p["spell_match"] == 1,
    "first match of a season": lambda p: p["season_match"] == 1,
    "last match before a missed season": lambda p: p["gap_after"] > NEW_SPELL_GAP_DAYS,
}


def side_positions(matches: pd.DataFrame) -> pd.DataFrame:
    """Per team per match: match number in the season and in the spell, whether the team is
    promoted (absent from the previous season, which must be in the table), and the days since
    its previous match and until its next one."""
    long = long_table(matches)
    seasons = sorted(matches["season"].unique())
    previous = dict(zip(seasons[1:], seasons[:-1]))
    teams = matches.groupby("season")["home"].agg(set)
    dates = long.groupby("team")["date"]
    return long[["match", "team", "season"]].assign(
        season_match=long.groupby(["team", "season"]).cumcount() + 1,
        spell_match=long.groupby(["team", "spell"]).cumcount() + 1,
        promoted=[season in previous and team not in teams[previous[season]]
                  for team, season in zip(long["team"], long["season"])],
        gap_before=dates.diff().dt.days,
        gap_after=-dates.diff(-1).dt.days,
    )


def matches_where(positions: pd.DataFrame, condition: Condition) -> list[int]:
    """Matches where either side meets the condition, in index order."""
    return sorted(set(positions.loc[condition(positions), "match"]))


def random_sample(index: Iterable[object], size: int = SAMPLE_SIZE, seed: int = SEED) -> list[object]:
    """The first `size` of a seeded random draw of 50 (so smaller samples are prefixes)."""
    if size > SAMPLE_SIZE:
        raise ValueError(f"random samples hold at most {SAMPLE_SIZE} matches")
    return random.Random(seed).sample(list(index), SAMPLE_SIZE)[:size]


def shuffled(candidates: Sequence[object], seed: int = SEED) -> list[object]:
    """A seeded random order of the candidates."""
    return random.Random(seed).sample(sorted(candidates), len(candidates))


def targeted_sample(matches: pd.DataFrame, target: str, size: int | None = PLANTED_SAMPLE,
                    within: Iterable[object] | None = None, seed: int = SEED) -> list[object]:
    """Up to `size` matches (all if None) of one TARGETS case, optionally only those in `within`."""
    candidates = matches_where(side_positions(matches), TARGETS[target])
    if within is not None:
        allowed = set(within)
        candidates = [match for match in candidates if match in allowed]
    return shuffled(candidates, seed)[:size]


def stratified_sample(matches: pd.DataFrame, size: int = SAMPLE_SIZE, per_stratum: int = PER_STRATUM,
                      seed: int = SEED) -> list[object]:
    """`size` matches holding at least `per_stratum` from every STRATA case (all of a smaller
    one), the rest drawn at random from the remaining matches."""
    rng, positions, chosen = random.Random(seed), side_positions(matches), []
    for condition in STRATA.values():
        members, taken = matches_where(positions, condition), set(chosen)
        pool = [match for match in members if match not in taken]
        shortfall = per_stratum - len(taken.intersection(members))
        chosen += rng.sample(pool, min(max(shortfall, 0), len(pool)))
    taken = set(chosen)
    rest = [match for match in matches.index if match not in taken]
    return chosen + rng.sample(rest, size - len(chosen))
