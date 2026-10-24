"""Stage 8 availability and form features, each as home_X, away_X and X_diff (home minus away).

All values for a match on date d come from FPL rows and matches dated strictly before d.
1) suspension: share of the team's last-10-match minutes played by players suspended for
   this match (Stage 7 ban rules).
2) squad_value: FPL price sum of the team's 11 key players, divided by the league-wide mean
   of that sum at the same moment, so price drift cancels. The mean is over the season's
   teams that have played before d, each valued as of d; a mean over the whole season
   would look ahead.
3) form: minutes-weighted mean BPS (form_bps) and ICT index (form_ict) over the previous 5 matches.
4) recent_absence (INJURY PROXY, not injury data): key set = top 11 by minutes over matches
   t-11 to t-2; the share of their minutes there that belongs to key players with 0 minutes
   (or not listed) in match t-1. NaN for a team's first 5 matches of each season, when
   summer departures would look like absences.
"""

from collections import Counter

import numpy as np
import pandas as pd

from src.availability import KEY_WINDOW, FORM_WINDOW, History, key_players, prior_matches, suspended, value_sum, weighted_mean

GROUPS = {
    "suspension": ["suspension"],
    "squad_value": ["squad_value"],
    "form": ["form_bps", "form_ict"],
    "recent_absence": ["recent_absence"],
}
ABSENCE_SEASON_START = 5  # recent_absence is NaN for a team's first 5 matches of a season
SIDES = ("home", "away")


def group_columns(groups: list[str]) -> list[str]:
    """Model columns (home_X, away_X, X_diff) for the named groups, in order."""
    return [column for group in groups for name in GROUPS[group]
            for column in (f"home_{name}", f"away_{name}", f"{name}_diff")]


def minutes_by_player(rows: pd.DataFrame) -> Counter:
    """Total minutes per player over the rows."""
    totals = Counter()
    for player, played in rows[["player", "minutes"]].values:
        totals[player] += played
    return totals


def suspension_share(history: History, team: str, prior: pd.DataFrame) -> float:
    """Share of the last-10-match minutes played by players banned for this match."""
    if prior.empty:
        return float("nan")
    minutes = minutes_by_player(history.rows_for(team, prior.tail(KEY_WINDOW)["date"]))
    total = sum(minutes.values())
    reds, yellows = suspended(history, team, prior.iloc[-1])
    return sum(minutes[player] for player in set(reds) | set(yellows)) / total if total else float("nan")


def key_value(history: History, team: str, date: pd.Timestamp) -> float:
    """FPL price sum, as of `date`, of the team's key players before `date` (NaN without any)."""
    prior = prior_matches(history.schedules.get(team, pd.DataFrame(columns=["date"])), date)
    keys = key_players(history.rows_for(team, prior.tail(KEY_WINDOW)["date"]))
    return value_sum(history, keys, date)[0] if keys else float("nan")


def season_teams_before(history: History, season: str, date: pd.Timestamp) -> list[str]:
    """Teams with a match in `season` dated before `date`."""
    return sorted(team for team, schedule in history.schedules.items()
                  if ((schedule["season"] == season) & (schedule["date"] < date)).any())


def league_key_value(history: History, season: str, date: pd.Timestamp, cache: dict) -> float:
    """Mean key value as of `date` over the season's teams that have played before `date`."""
    values = []
    for team in season_teams_before(history, season, date):
        if (team, date) not in cache:
            cache[(team, date)] = key_value(history, team, date)
        values.append(cache[(team, date)])
    values = [value for value in values if not np.isnan(value)]
    return float(np.mean(values)) if values else float("nan")


def absence_match_date(prior: pd.DataFrame, date: pd.Timestamp) -> pd.Timestamp:
    """The match whose minutes define absence: the team's previous match, t-1."""
    return prior.iloc[-1]["date"]


def recent_absence(history: History, team: str, season: str, prior: pd.DataFrame, date: pd.Timestamp) -> float:
    """Injury proxy: share of key-set minutes (t-11..t-2) from key players who didn't play t-1."""
    match_number = int((prior["season"] == season).sum()) + 1
    if match_number <= ABSENCE_SEASON_START or len(prior) < 2:
        return float("nan")
    window_rows = history.rows_for(team, prior.iloc[-(KEY_WINDOW + 1):-1]["date"])
    keys, window_minutes = key_players(window_rows), minutes_by_player(window_rows)
    played_last = minutes_by_player(history.rows_for(team, pd.Series([absence_match_date(prior, date)])))
    total = sum(window_minutes[player] for player in keys)
    absent = [player for player in keys if played_last.get(player, 0) == 0]
    return sum(window_minutes[player] for player in absent) / total if total else float("nan")


def side_features(history: History, team: str, season: str, date: pd.Timestamp, league_value: float) -> dict[str, float]:
    """Every Stage 8 feature for one team before a match on `date`."""
    prior = prior_matches(history.schedules.get(team, pd.DataFrame(columns=["date", "season", "match_number"])), date)
    form_rows = history.rows_for(team, prior.tail(FORM_WINDOW)["date"])
    return {
        "suspension": suspension_share(history, team, prior),
        "squad_value": key_value(history, team, date) / league_value,
        "form_bps": weighted_mean(form_rows, "bps"),
        "form_ict": weighted_mean(form_rows, "ict_index"),
        "recent_absence": recent_absence(history, team, season, prior, date),
    }


def build_availability_features(rows: pd.DataFrame, matches: pd.DataFrame, only: list[object] | None = None) -> pd.DataFrame:
    """Stage 8 features per match, indexed like `matches` (`only` limits which are computed)."""
    history = History.build(rows, matches)
    targets = matches if only is None else matches.loc[only]
    cache: dict = {}
    records = {}
    for index, match in targets.iterrows():
        league_value = league_key_value(history, match["season"], match["date"], cache)
        sides = {side: side_features(history, match[side], match["season"], match["date"], league_value) for side in SIDES}
        record = {f"{side}_{name}": value for side in SIDES for name, value in sides[side].items()}
        record |= {f"{name}_diff": sides["home"][name] - sides["away"][name] for name in sides["home"]}
        records[index] = record
    features = pd.DataFrame.from_dict(records, orient="index")
    return pd.concat([targets[["date", "season", "home", "away"]], features], axis=1)
