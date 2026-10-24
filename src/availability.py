"""Point-in-time availability and form values per match (audit only; not in any model).

Every value for a match on date d comes from FPL rows of matches dated strictly before d
(CLAUDE.md prediction time rule): the match's own rows are never read.
- Suspensions: a red card in a team's league match bans the player for that team's next
  league match; reaching 5 yellows by the team's 19th match, 10 by its 32nd or 15 by its
  38th does the same. Yellows in a match where the player was sent off don't count.
- Key players: the 11 players with most minutes in the team's previous 10 league matches.
- Squad value: each player's latest FPL price dated before d (a proxy; Transfermarkt
  market values are off limits), summed over the squad and over the key players. The squad
  is the squad list as of d: the players FPL lists for the team in this fixture. Only who is
  listed is used, never the listed rows' values.
- Form: minutes-weighted mean BPS and ICT index over the team's previous 5 matches.
- Injuries: no legitimate dated source exists here; unavailable_at_kickoff implements the
  rule for when one does.
"""

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

KEY_PLAYERS = 11
KEY_WINDOW = 10
FORM_WINDOW = 5
YELLOW_THRESHOLDS = ((5, 19), (10, 32), (15, 38))  # (yellows, by the team's nth league match)
SIDES = ("home", "away")


def team_schedule(matches: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Per team, its league matches in date order with the team's match number in the season."""
    long = pd.concat([matches[["date", "season", side]].rename(columns={side: "team"}) for side in SIDES])
    long = long.sort_values(["team", "date"], kind="stable")
    long["match_number"] = long.groupby(["team", "season"]).cumcount() + 1
    return {team: frame.reset_index(drop=True) for team, frame in long.groupby("team")}


def prior_matches(schedule: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    """The team's league matches dated strictly before `date`."""
    return schedule[schedule["date"] < date]


def snapshot_cutoff(dates: np.ndarray, date: np.datetime64) -> int:
    """How many of a player's (sorted) snapshot dates fall strictly before `date`."""
    return int(np.searchsorted(dates, date, side="left"))


def unavailable_at_kickoff(spells: pd.DataFrame, date: pd.Timestamp) -> set[object]:
    """Players in an injury/suspension spell at kickoff on `date`: the spell started before
    the match date and has no recorded return date on or before it. The return date is
    used for nothing else."""
    started = spells["start"] < date
    still_out = spells["end"].isna() | (spells["end"] > date)
    return set(spells.loc[started & still_out, "player"])


def count_missing_end_dates(spells: pd.DataFrame) -> int:
    """Spells without a recorded return date."""
    return int(spells["end"].isna().sum())


ROW_COLUMNS = ["player", "minutes", "yellow_cards", "red_cards", "bps", "ict_index"]


@dataclass
class History:
    """FPL rows (linked to football-data dates) indexed by position for as-of lookups."""

    schedules: dict[str, pd.DataFrame]
    rows: pd.DataFrame  # sorted by team, date
    team_rows: dict[tuple[str, pd.Timestamp], np.ndarray]  # (team, date) -> positions in rows
    price_dates: np.ndarray  # sorted by player, date
    price_values: np.ndarray
    price_rows: dict[object, np.ndarray]  # player -> positions in price arrays
    yellow_dates: np.ndarray  # yellows from matches without a red, sorted by player, season, date
    yellow_counts: np.ndarray
    yellow_rows: dict[tuple[object, str], np.ndarray]

    @classmethod
    def build(cls, rows: pd.DataFrame, matches: pd.DataFrame) -> "History":
        by_team = rows.sort_values(["team", "date"], kind="stable").reset_index(drop=True)
        by_player = rows.sort_values(["player", "date"], kind="stable").reset_index(drop=True)
        counted = by_player[by_player["red_cards"] == 0].sort_values(["player", "season", "date"], kind="stable")
        counted = counted.reset_index(drop=True)
        return cls(
            schedules=team_schedule(matches),
            rows=by_team[ROW_COLUMNS],
            team_rows=by_team.groupby(["team", "date"]).indices,
            price_dates=by_player["date"].to_numpy(), price_values=by_player["price"].to_numpy(),
            price_rows=by_player.groupby("player").indices,
            yellow_dates=counted["date"].to_numpy(), yellow_counts=counted["yellow_cards"].to_numpy(),
            yellow_rows=counted.groupby(["player", "season"]).indices,
        )

    def has_rows(self, team: str, date: pd.Timestamp) -> bool:
        return (team, date) in self.team_rows

    def rows_for(self, team: str, dates: pd.Series) -> pd.DataFrame:
        """The team's player rows across the given match dates (empty if none)."""
        positions = [self.team_rows[(team, day)] for day in dates if (team, day) in self.team_rows]
        return self.rows.iloc[np.concatenate(positions)] if positions else self.rows.iloc[:0]

    def yellows_through(self, player: object, season: str, date: pd.Timestamp) -> int:
        """Counted yellows for a player in a season up to and including `date`."""
        positions = self.yellow_rows.get((player, season), np.array([], dtype=int))
        return int(self.yellow_counts[positions][self.yellow_dates[positions] <= np.datetime64(date)].sum())

    def latest_price(self, player: object, date: pd.Timestamp) -> float:
        """The player's latest FPL price from a row dated before `date` (NaN if none)."""
        positions = self.price_rows.get(player, np.array([], dtype=int))
        cutoff = snapshot_cutoff(self.price_dates[positions], np.datetime64(date))
        return float(self.price_values[positions][cutoff - 1]) if cutoff else float("nan")


def suspended(history: History, team: str, last: pd.Series) -> tuple[list[object], list[object]]:
    """(red-card bans, yellow-accumulation bans) carried from the team's previous match `last`."""
    rows = history.rows_for(team, pd.Series([last["date"]]))
    reds = sorted(rows.loc[rows["red_cards"] > 0, "player"])
    yellows = []
    for player, cards in rows.loc[(rows["red_cards"] == 0) & (rows["yellow_cards"] > 0), ["player", "yellow_cards"]].values:
        after = history.yellows_through(player, last["season"], last["date"])
        before = after - cards
        if any(before < count <= after and last["match_number"] <= by for count, by in YELLOW_THRESHOLDS):
            yellows.append(player)
    return reds, sorted(yellows)


def key_players(window_rows: pd.DataFrame) -> list[object]:
    """Top 11 by minutes over the window (ties by player id), players with minutes only."""
    minutes = Counter()
    for player, played in window_rows[["player", "minutes"]].values:
        minutes[player] += played
    ranked = sorted((player for player, played in minutes.items() if played > 0),
                    key=lambda player: (-minutes[player], player))
    return ranked[:KEY_PLAYERS]


def weighted_mean(rows: pd.DataFrame, column: str) -> float:
    """Minutes-weighted mean of `column` over the rows (NaN without minutes)."""
    minutes = rows["minutes"].astype(float)
    total = minutes.sum()
    return float((minutes * rows[column].astype(float)).sum() / total) if total > 0 else float("nan")


def squad_list(history: History, team: str, date: pd.Timestamp) -> list[object]:
    """The squad list as of `date`: who FPL lists for the team in that fixture (identity only)."""
    return sorted(history.rows_for(team, pd.Series([date]))["player"])


def value_sum(history: History, players: list[object], date: pd.Timestamp) -> tuple[float, int]:
    """(sum of latest prices before `date`, how many players had one); NaN sum if none did."""
    prices = [price for price in (history.latest_price(player, date) for player in players) if not np.isnan(price)]
    return (float(sum(prices)) if prices else float("nan")), len(prices)


def team_values(history: History, team: str, date: pd.Timestamp) -> dict[str, object]:
    """Every availability value for one team before a match on `date`."""
    prior = prior_matches(history.schedules.get(team, pd.DataFrame(columns=["date", "season", "match_number"])), date)
    key_window, form_window = prior.tail(KEY_WINDOW), prior.tail(FORM_WINDOW)
    keys = key_players(history.rows_for(team, key_window["date"]))
    squad = squad_list(history, team, date)
    reds, yellows = suspended(history, team, prior.iloc[-1]) if not prior.empty else ([], [])
    form_rows = history.rows_for(team, form_window["date"])
    squad_value, squad_priced = value_sum(history, squad, date)
    key_value, _ = value_sum(history, keys, date)
    return {
        "fpl_window": sum(history.has_rows(team, day) for day in key_window["date"]),
        "banned_red": reds, "banned_yellow": yellows, "n_suspended": len(set(reds) | set(yellows)),
        "key_players": keys, "key_in_squad": len(set(keys) & set(squad)),
        "squad_size": len(squad), "squad_priced": squad_priced, "squad_value": squad_value,
        "key_value": key_value if keys else float("nan"),
        "form_bps": weighted_mean(form_rows, "bps"), "form_ict": weighted_mean(form_rows, "ict_index"),
    }


def build_availability(rows: pd.DataFrame, matches: pd.DataFrame, only: list[object] | None = None) -> pd.DataFrame:
    """Availability values per match (home_/away_ prefixed), indexed like `matches`.

    `rows` are linked FPL rows (see name_maps.link_rows); `only` limits which matches are
    computed, using the same history.
    """
    history = History.build(rows, matches)
    targets = matches if only is None else matches.loc[only]
    records = {}
    for index, match in targets.iterrows():
        record = {}
        for side in SIDES:
            record |= {f"{side}_{name}": value for name, value in team_values(history, match[side], match["date"]).items()}
        records[index] = record
    values = pd.DataFrame.from_dict(records, orient="index")
    return pd.concat([targets[["date", "season", "home", "away"]], values], axis=1)
