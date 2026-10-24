"""Gate L leakage checks for the v2-pre injury features (docs/v2_lineup_plan.md amendment A2).

v2-pre predicts before lineups, so a match's features are rebuilt from the matches, lineups and
injury lists dated strictly before it plus that fixture's own injury list only: its own XI and bench
are removed, its result and stats are scrambled, and other matches on the same day are left out.
The rebuilt features must equal those built from the full tables. Planted leaks: reading the
match's own XI, and reading the team's next fixture's injury list.
"""

import pandas as pd

import src.injury_features as injury_features
from src.injury_features import Spell, build_injury_features
from src.leak_checks import earlier_plus_scrambled, features_differ, planted
from src.leak_samples import PLANTED_SAMPLE, shuffled
from src.lineup_features import TeamMatch, team_histories
from src.lineup_leaks import lineup_matches, random_matches

Tables = tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]


def earlier_plus_own_list(matches: pd.DataFrame, lineups: pd.DataFrame, injuries: pd.DataFrame,
                          target: int) -> Tables:
    """Matches, lineups and injury records before the target, plus the target with its result and
    stats scrambled and its own injury list (its lineup removed)."""
    rebuilt = earlier_plus_scrambled(matches, target)
    earlier = set(rebuilt.index) - {target}
    return (rebuilt, lineups[lineups["match"].isin(earlier)],
            injuries[injuries["match"].isin(earlier | {target})])


def flagged(matches: pd.DataFrame, lineups: pd.DataFrame, injuries: pd.DataFrame, covered: set[str],
            full: pd.DataFrame, targets: list[int]) -> int:
    """How many targets' rebuilt features differ from `full` (built by the same code)."""
    return sum(features_differ(build_injury_features(*earlier_plus_own_list(matches, lineups, injuries, target),
                                                     covered).loc[target], full.loc[target]) for target in targets)


def regulars_not_starting(team_match: TeamMatch, listed: frozenset[int], regulars: list[int] | None) -> frozenset[int]:
    """PLANTED LEAK: regulars missing from the match's own XI treated as missing (the XI is not
    known when v2-pre predicts)."""
    if team_match.xi is None or regulars is None:
        return listed
    return frozenset(player for player in regulars if player not in team_match.xi)


def next_fixture_list(missing: dict[tuple[int, str], frozenset[int]], spell: Spell, position: int) -> frozenset[int]:
    """PLANTED LEAK: the team's next fixture's injury list."""
    if position + 1 >= len(spell):
        return frozenset()
    venue, team_match = spell[position + 1]
    return missing.get((team_match.match, venue), frozenset())


OWN_XI_TARGET = "a side with a regular XI and a lineup for the match"
NEXT_LIST_TARGET = "a side whose next fixture lists a missing player"
INJURY_LEAKS = [  # (check, function replaced in src.injury_features, leaky version, targeted sample)
    ("the match's own XI read", "missing_players", regulars_not_starting, OWN_XI_TARGET),
    ("the next fixture's injury list read", "fixture_list", next_fixture_list, NEXT_LIST_TARGET),
]


def injury_targets(matches: pd.DataFrame, lineups: pd.DataFrame, injuries: pd.DataFrame,
                   covered: set[str]) -> dict[str, list[int]]:
    """Covered matches with both lineups where either side is in each targeted case."""
    both = {match for match in lineup_matches(lineups) if matches.at[match, "season"] in covered}
    listed = set(map(tuple, injury_features.listed_missing(injuries)[["match", "side"]].itertuples(index=False)))
    own_xi, next_list = set(), set()
    for spell in team_histories(matches, lineups).values():
        known = 0
        for position, (venue, team_match) in enumerate(spell):
            if team_match.xi is not None:
                if known >= 3:
                    own_xi.add(team_match.match)
                known += 1
            if position + 1 < len(spell) and (spell[position + 1][1].match, spell[position + 1][0]) in listed:
                next_list.add(team_match.match)
    return {OWN_XI_TARGET: sorted(both & own_xi), NEXT_LIST_TARGET: sorted(both & next_list)}


def injury_check_report(matches: pd.DataFrame, lineups: pd.DataFrame, injuries: pd.DataFrame, covered: set[str],
                        limit: int | None = None) -> pd.DataFrame:
    """v2-pre Gate L counts: the real code on a random sample, then each planted leak on a random and
    a targeted sample with the real code on that targeted sample."""
    def capped(sample: list[int]) -> list[int]:
        return sample if limit is None else sample[:limit]

    both = [match for match in lineup_matches(lineups) if matches.at[match, "season"] in covered]
    targets = injury_targets(matches, lineups, injuries, covered)
    real = build_injury_features(matches, lineups, injuries, covered)
    at_random = capped(random_matches(both, PLANTED_SAMPLE))
    rows = [{"check": "real code: rebuilt from earlier data plus the fixture's own injury list",
             "random_cases": len(at_random), "random_flagged": flagged(matches, lineups, injuries, covered, real, at_random)}]
    for check, name, leaky, target in INJURY_LEAKS:
        targeted = capped(shuffled(targets[target])[:PLANTED_SAMPLE])
        real_flags = flagged(matches, lineups, injuries, covered, real, targeted)
        with planted(injury_features, name, leaky):
            full = build_injury_features(matches, lineups, injuries, covered)
            rows.append({"check": check, "random_cases": len(at_random),
                         "random_flagged": flagged(matches, lineups, injuries, covered, full, at_random),
                         "targeted_sample": target, "targeted_cases": len(targeted),
                         "targeted_flagged": flagged(matches, lineups, injuries, covered, full, targeted),
                         "real_code_targeted_flagged": real_flags})
    return pd.DataFrame(rows).astype({column: "Int64" for column in
                                      ["random_cases", "random_flagged", "targeted_cases", "targeted_flagged",
                                       "real_code_targeted_flagged"]})


def real_code_flags(report: pd.DataFrame) -> int:
    """Matches flagged on the real code in an injury check report (should be 0)."""
    real = report["check"].str.startswith("real code")
    return int(report.loc[real, "random_flagged"].sum() + report["real_code_targeted_flagged"].sum())
