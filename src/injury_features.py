"""v2-pre injury features (docs/v2_lineup_plan.md amendment A2), per team and fixture.

- injured_regulars: the share of the team's regular XI (src/lineup_features.py's definition, built
  from earlier matches' lineups only) listed as missing the fixture ("Missing Fixture" records).
  Missing when the regular XI is missing.
- injured_count: the number of the team's players listed as missing the fixture (0 when none are).
Both are missing in seasons without injury coverage. v2-pre predicts before lineups are published,
so the match's own XI is never used. fixture_list and missing_players are module-level so that
leakage checks can replace them with planted leaks (src/injury_leaks.py).
"""

import numpy as np
import pandas as pd

from src.features import differences, side
from src.injuries import listed_missing
from src.lineup_features import XI_SIZE, TeamMatch, regular_xi, team_histories, window_matches

FEATURES = ["injured_regulars", "injured_count"]
Spell = list[tuple[str, TeamMatch]]


def missing_index(injuries: pd.DataFrame) -> dict[tuple[int, str], frozenset[int]]:
    """(match, side) -> players listed as missing, from match_injuries rows."""
    listed = listed_missing(injuries)
    return {(int(match), venue): frozenset(rows["player_id"].astype(int))
            for (match, venue), rows in listed.groupby(["match", "side"])}


def fixture_list(missing: dict[tuple[int, str], frozenset[int]], spell: Spell, position: int) -> frozenset[int]:
    """The players listed as missing this fixture for this team."""
    venue, team_match = spell[position]
    return missing.get((team_match.match, venue), frozenset())


def missing_players(team_match: TeamMatch, listed: frozenset[int], regulars: list[int] | None) -> frozenset[int]:
    """The players treated as missing: the fixture's list. The match's own XI is not read."""
    return listed


def match_injury_features(spell: Spell, position: int, missing: dict[tuple[int, str], frozenset[int]],
                          covered: bool) -> dict[str, float]:
    """The two features for the team's match at `position` of its spell."""
    if not covered:
        return dict.fromkeys(FEATURES, np.nan)
    team_match = spell[position][1]
    regulars = regular_xi(window_matches([match for _, match in spell], position))
    out = missing_players(team_match, fixture_list(missing, spell, position), regulars)
    return {"injured_regulars": np.nan if regulars is None else len(out & set(regulars)) / XI_SIZE,
            "injured_count": float(len(out))}


def build_injury_features(matches: pd.DataFrame, lineups: pd.DataFrame, injuries: pd.DataFrame,
                          covered_seasons: set[str]) -> pd.DataFrame:
    """Injury features indexed like `matches`: home_X, away_X and X_diff for each of FEATURES."""
    missing, rows = missing_index(injuries), []
    for spell in team_histories(matches, lineups).values():
        rows += [{"match": team_match.match, "venue": venue,
                  **match_injury_features(spell, position, missing, matches.at[team_match.match, "season"] in covered_seasons)}
                 for position, (venue, team_match) in enumerate(spell)]
    per_team = pd.DataFrame(rows, columns=["match", "venue", *FEATURES])
    home, away = side(per_team, "home"), side(per_team, "away")
    return pd.concat([home, away, differences(home, away)], axis=1).reindex(matches.index)
