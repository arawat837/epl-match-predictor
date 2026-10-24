"""API-Football injury lists for the pre-lineup variant v2-pre (docs/v2_lineup_plan.md amendment A2):
requests, parsing from the raw cache, linking to matches, and Gate I.

A record says a player is expected to miss (type "Missing Fixture") or may miss ("Questionable") a
fixture. Only "Missing Fixture" records count as listed missing. Gate I: if more than 2% of those
records name a player who started that fixture, the lists were written or edited after kickoff and
v2-pre is dropped.
"""

from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd

from src.api_football import CACHE_DIR, PREMIER_LEAGUE, Request
from src.lineups import canonical_team, read_cached

MISSING = "Missing Fixture"
GATE_I_MAX_SHARE = 0.02
INJURY_COLUMNS = ["fixture_id", "team_id", "team", "player_id", "player", "type", "reason"]


def injuries_request(season: int, page: int = 1) -> Request:
    params: dict[str, object] = {"league": PREMIER_LEAGUE, "season": season}
    return "injuries", params if page == 1 else params | {"page": page}


def page_count(payload: Mapping[str, object]) -> int:
    return int((payload.get("paging") or {}).get("total") or 1)


def injury_requests(seasons: Iterable[int], cache_dir: Path = CACHE_DIR) -> list[Request]:
    """Each season's first page, plus its further pages once the first page is cached."""
    requests = []
    for season in seasons:
        requests.append(injuries_request(season))
        first = read_cached(injuries_request(season), cache_dir)
        if first is not None:
            requests += [injuries_request(season, page) for page in range(2, page_count(first) + 1)]
    return requests


def injury_rows(payload: Mapping[str, object]) -> pd.DataFrame:
    """One row per record of an /injuries response."""
    rows = [{"fixture_id": item["fixture"]["id"], "team_id": item["team"]["id"],
             "team": canonical_team(item["team"]["name"]), "player_id": item["player"]["id"],
             "player": item["player"].get("name"), "type": item["player"].get("type"),
             "reason": item["player"].get("reason")}
            for item in payload["response"]]
    return pd.DataFrame(rows, columns=INJURY_COLUMNS)


def load_injuries(seasons: Iterable[int], cache_dir: Path = CACHE_DIR) -> tuple[pd.DataFrame, list[int]]:
    """Records of every season whose pages are all cached, and the seasons with at least one page
    missing (left out entirely)."""
    tables, incomplete = [], []
    for season in seasons:
        first = read_cached(injuries_request(season), cache_dir)
        payloads = [first] + [read_cached(injuries_request(season, page), cache_dir)
                              for page in range(2, page_count(first) + 1)] if first else [None]
        if any(payload is None for payload in payloads):
            incomplete.append(season)
            continue
        tables += [injury_rows(payload) for payload in payloads]
    injuries = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=INJURY_COLUMNS)
    return injuries.drop_duplicates(["fixture_id", "player_id", "type"]).reset_index(drop=True), incomplete


def listed_missing(injuries: pd.DataFrame) -> pd.DataFrame:
    """Records whose type says the player will miss the fixture."""
    return injuries[injuries["type"] == MISSING]


def gate_i(injuries: pd.DataFrame, lineups: pd.DataFrame) -> dict[str, object]:
    """Gate I on fixtures that have both a lineup and injury records: how many "Missing Fixture"
    records name one of that fixture's starters."""
    starters = lineups.loc[lineups["starter"], ["fixture_id", "player_id"]].drop_duplicates()
    missing = listed_missing(injuries)
    checked = missing[missing["fixture_id"].isin(set(lineups["fixture_id"]))]
    named = checked.merge(starters, on=["fixture_id", "player_id"], how="inner")
    share = len(named) / len(checked) if len(checked) else float("nan")
    return {"fixtures_checked": int(checked["fixture_id"].nunique()), "records_checked": len(checked),
            "records_naming_a_starter": len(named), "share": share,
            "passed": bool(len(checked)) and share <= GATE_I_MAX_SHARE}


def match_injuries(injuries: pd.DataFrame, linked: pd.DataFrame) -> pd.DataFrame:
    """Injury records with their match index and side, for linked fixtures only."""
    sides = linked.dropna(subset=["match"])[["fixture_id", "match", "home_id", "away_id"]]
    rows = injuries.merge(sides, on="fixture_id", how="inner")
    home, away = rows["team_id"] == rows["home_id"], rows["team_id"] == rows["away_id"]
    if not (home | away).all():
        raise ValueError(f"injury teams not in their fixture: {sorted(set(rows.loc[~(home | away), 'fixture_id']))}")
    rows["side"] = home.map({True: "home", False: "away"})
    return rows.drop(columns=["home_id", "away_id"]).astype({"match": "int64"})
