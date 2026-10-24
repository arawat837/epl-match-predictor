"""Premier League fixtures and announced starting XIs from API-Football's cached responses, linked to
matches.parquet (v2 lineup plan, docs/v2_lineup_plan.md).

Reads only the raw cache under data/raw/api_football/; fetching is src/api_football.py's job. Player
identity is API-Football's player id. A fixture's lineup counts only if both teams have 11 starters.
"""

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd

from src.api_football import CACHE_DIR, PREMIER_LEAGUE, Request, cache_path
from src.forward import UK
from src.seasons import season_label
from src.teams import TEAM_NAMES

API_TEAM_NAMES = {"Sheffield Utd": "Sheffield United"}  # API names that are neither a key nor a value of TEAM_NAMES
FINISHED = {"FT", "AET", "PEN"}
LINK_THRESHOLD = 0.99  # Gate L: share of API fixtures that must link to matches.parquet
XI_SIZE = 11
MATCH_KEY = ["date", "home", "away"]
LINEUP_COLUMNS = ["fixture_id", "team_id", "team", "player_id", "player", "position", "starter"]


def canonical_team(name: str) -> str:
    """Full club name for an API-Football team name; raises on a name it cannot map."""
    if name in API_TEAM_NAMES:
        return API_TEAM_NAMES[name]
    if name in TEAM_NAMES:
        return TEAM_NAMES[name]
    if name in TEAM_NAMES.values():
        return name
    raise ValueError(f"Unknown API-Football team name {name!r}; add it to API_TEAM_NAMES in src/lineups.py")


def fixtures_request(season: int) -> Request:
    return "fixtures", {"league": PREMIER_LEAGUE, "season": season}


def lineup_request(fixture_id: int) -> Request:
    return "fixtures/lineups", {"fixture": fixture_id}


def round_number(round_name: str) -> int:
    """'Regular Season - 7' -> 7."""
    return int(round_name.rsplit("-", 1)[-1])


def fixture_table(payload: Mapping[str, object]) -> pd.DataFrame:
    """One row per fixture of a /fixtures response: id, UTC kickoff, UK date, season, round, teams, status."""
    rows = []
    for item in payload["response"]:
        kickoff = pd.Timestamp(item["fixture"]["date"]).tz_convert("UTC")
        rows.append({"fixture_id": item["fixture"]["id"], "kickoff": kickoff,
                     "date": kickoff.tz_convert(UK).tz_localize(None).normalize(),
                     "season": season_label(item["league"]["season"]), "round": round_number(item["league"]["round"]),
                     "home": canonical_team(item["teams"]["home"]["name"]),
                     "away": canonical_team(item["teams"]["away"]["name"]),
                     "home_id": item["teams"]["home"]["id"], "away_id": item["teams"]["away"]["id"],
                     "status": item["fixture"]["status"]["short"]})
    return pd.DataFrame(rows).sort_values(["kickoff", "fixture_id"], ignore_index=True)


def lineup_rows(fixture_id: int, payload: Mapping[str, object]) -> pd.DataFrame:
    """One row per listed player (starters and bench) of a /fixtures/lineups response."""
    rows = [{"fixture_id": fixture_id, "team_id": side["team"]["id"], "team": canonical_team(side["team"]["name"]),
             "player_id": entry["player"]["id"], "player": entry["player"]["name"],
             "position": entry["player"].get("pos"), "starter": starter}
            for side in payload["response"]
            for starter, group in ((True, "startXI"), (False, "substitutes"))
            for entry in side.get(group) or []]
    return pd.DataFrame(rows, columns=LINEUP_COLUMNS)


def complete(lineups: pd.DataFrame) -> bool:
    """Both teams listed, each with 11 starters with player ids."""
    starters = lineups[lineups["starter"] & lineups["player_id"].notna()]
    counts = starters.groupby("team_id")["player_id"].nunique()
    return len(counts) == 2 and bool((counts == XI_SIZE).all())


def read_cached(request: Request, cache_dir: Path = CACHE_DIR) -> dict | None:
    path = cache_path(*request, cache_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_fixtures(seasons: Iterable[int], cache_dir: Path = CACHE_DIR) -> pd.DataFrame:
    """Every finished fixture of the cached seasons (a season whose list is not cached is skipped)."""
    tables = [fixture_table(payload) for season in seasons
              if (payload := read_cached(fixtures_request(season), cache_dir)) is not None]
    if not tables:
        return pd.DataFrame(columns=["fixture_id", "kickoff", "date", "season", "round", "home", "away"])
    fixtures = pd.concat(tables, ignore_index=True)
    return fixtures[fixtures["status"].isin(FINISHED)].reset_index(drop=True)


def load_lineups(fixture_ids: Iterable[int], cache_dir: Path = CACHE_DIR) -> tuple[pd.DataFrame, list[int]]:
    """Lineup rows of every cached, complete fixture, and the cached fixtures left out as incomplete."""
    tables, incomplete = [], []
    for fixture_id in fixture_ids:
        payload = read_cached(lineup_request(fixture_id), cache_dir)
        if payload is None:
            continue
        rows = lineup_rows(fixture_id, payload)
        if complete(rows):
            tables.append(rows)
        else:
            incomplete.append(fixture_id)
    lineups = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=LINEUP_COLUMNS)
    return lineups, incomplete


def fetch_order(fixtures: pd.DataFrame, seasons: Iterable[int]) -> list[int]:
    """Fixture ids season by season in the given order, round by round within a season, so that
    every team's run of lineups grows without gaps."""
    rank = {season_label(season): position for position, season in enumerate(seasons)}
    ordered = fixtures.assign(season_rank=fixtures["season"].map(rank)).dropna(subset=["season_rank"])
    return ordered.sort_values(["season_rank", "round", "kickoff", "fixture_id"])["fixture_id"].tolist()


def link_fixtures(fixtures: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Fixtures with the index of the matches.parquet row of the same UK date, home and away team
    (`match`, missing when there is none)."""
    keyed = matches[MATCH_KEY].assign(match=matches.index)
    return fixtures.merge(keyed, on=MATCH_KEY, how="left").astype({"match": "Int64"})


def link_rate(linked: pd.DataFrame) -> float:
    return float(linked["match"].notna().mean()) if len(linked) else float("nan")


def match_lineups(lineups: pd.DataFrame, linked: pd.DataFrame) -> pd.DataFrame:
    """Lineup rows with their match index and side (home or away), for linked fixtures only."""
    sides = linked.dropna(subset=["match"])[["fixture_id", "match", "home_id", "away_id"]]
    rows = lineups.merge(sides, on="fixture_id", how="inner")
    home, away = rows["team_id"] == rows["home_id"], rows["team_id"] == rows["away_id"]
    if not (home | away).all():
        raise ValueError(f"lineup teams not in their fixture: {sorted(set(rows.loc[~(home | away), 'fixture_id']))}")
    rows["side"] = home.map({True: "home", False: "away"})
    return rows.drop(columns=["home_id", "away_id"]).astype({"match": "int64"})
