"""v2 lineup features (docs/v2_lineup_plan.md section 5), per team and match, from Premier League
lineups only: the team's matches dated strictly before the match, plus that match's announced XI,
within a spell (a gap of more than 200 days since the team's previous match starts a new one).

- xi_regulars: share of the team's regular XI who start. The regular XI is the 11 players with the
  most starts over the team's previous 10 league matches in the spell; of those 10, only matches with
  lineup data count, and the value is missing if fewer than 3 do. Ties go to the more recent start,
  then the lower player id. Value = (regulars in the announced XI) / 11.
- xi_changes: starters not in the XI of the team's previous league match in the spell (0-11).
- keeper_changed: 1 if the starting goalkeeper differs from the previous league match's, else 0.

Every feature is missing when the match's own XI is missing; xi_changes and keeper_changed also when
there is no previous match in the spell or its XI (or goalkeeper) is missing. Each feature enters as
home_X, away_X and X_diff. The bench is carried only so leakage checks can plant a leak that reads
it; no feature uses it. starters, window_matches and previous_match are module-level functions so
that checks can replace them (src/lineup_leaks.py).
"""

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.features import differences, long_table, side

WINDOW = 10
MIN_WINDOW_LINEUPS = 3
XI_SIZE = 11
FEATURES = ["xi_regulars", "xi_changes", "keeper_changed"]


@dataclass(frozen=True)
class TeamMatch:
    """One team's league match: its date and, if known, its announced XI, goalkeeper and bench."""
    match: int
    date: pd.Timestamp
    xi: frozenset[int] | None
    keeper: int | None
    bench: frozenset[int]


def lineup_index(lineups: pd.DataFrame) -> dict[tuple[int, str], tuple[frozenset[int], int | None, frozenset[int]]]:
    """(match, side) -> (starters, starting goalkeeper or None, bench) from match_lineups rows."""
    index = {}
    for (match, venue), rows in lineups.groupby(["match", "side"]):
        starters = rows[rows["starter"]]
        keepers = starters.loc[starters["position"] == "G", "player_id"].tolist()
        index[(int(match), venue)] = (frozenset(starters["player_id"].astype(int)),
                                      int(keepers[0]) if len(keepers) == 1 else None,
                                      frozenset(rows.loc[~rows["starter"], "player_id"].astype(int)))
    return index


def team_histories(matches: pd.DataFrame, lineups: pd.DataFrame) -> dict[tuple[str, int], list[tuple[str, TeamMatch]]]:
    """Each team's league matches per spell in date order, as (venue, TeamMatch)."""
    known, histories = lineup_index(lineups), {}
    for row in long_table(matches).itertuples(index=False):
        xi, keeper, bench = known.get((int(row.match), row.venue), (None, None, frozenset()))
        histories.setdefault((row.team, row.spell), []).append(
            (row.venue, TeamMatch(int(row.match), row.date, xi, keeper, bench)))
    return histories


def starters(team_match: TeamMatch) -> frozenset[int]:
    """The players who start: the announced XI."""
    return team_match.xi


def window_matches(history: list[TeamMatch], position: int) -> list[TeamMatch]:
    """The team's previous WINDOW league matches in the spell."""
    return history[max(0, position - WINDOW):position]


def previous_match(history: list[TeamMatch], position: int) -> TeamMatch | None:
    """The team's previous league match in the spell."""
    return history[position - 1] if position > 0 else None


def regular_xi(window: list[TeamMatch]) -> list[int] | None:
    """The 11 players with most starts over the window's matches with lineups (ties: more recent
    start, then lower id), or None if fewer than MIN_WINDOW_LINEUPS of them have lineups."""
    known = [team_match for team_match in window if team_match.xi is not None]
    if len(known) < MIN_WINDOW_LINEUPS:
        return None
    starts, last_start = Counter(), {}
    for team_match in known:
        for player in starters(team_match):
            starts[player] += 1
            last_start[player] = max(last_start.get(player, team_match.date), team_match.date)
    return sorted(starts, key=lambda player: (-starts[player], -last_start[player].value, player))[:XI_SIZE]


def match_features(history: list[TeamMatch], position: int) -> dict[str, float]:
    """The three features for the team's match at `position` of its spell."""
    current = history[position]
    if current.xi is None:
        return dict.fromkeys(FEATURES, np.nan)
    regulars = regular_xi(window_matches(history, position))
    previous = previous_match(history, position)
    known_previous = previous is not None and previous.xi is not None
    keepers_known = known_previous and current.keeper is not None and previous.keeper is not None
    return {"xi_regulars": np.nan if regulars is None else len(starters(current) & set(regulars)) / XI_SIZE,
            "xi_changes": float(len(starters(current) - starters(previous))) if known_previous else np.nan,
            "keeper_changed": float(current.keeper != previous.keeper) if keepers_known else np.nan}


def build_lineup_features(matches: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    """Lineup features indexed like `matches`: home_X, away_X and X_diff for each of FEATURES."""
    rows = []
    for spell in team_histories(matches, lineups).values():
        history = [team_match for _, team_match in spell]
        rows += [{"match": team_match.match, "venue": venue, **match_features(history, position)}
                 for position, (venue, team_match) in enumerate(spell)]
    per_team = pd.DataFrame(rows, columns=["match", "venue", *FEATURES])
    home, away = side(per_team, "home"), side(per_team, "away")
    return pd.concat([home, away, differences(home, away)], axis=1).reindex(matches.index)
