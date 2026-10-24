"""API-Football access for the v2 lineup plan (docs/v2_lineup_plan.md): requests, a raw cache and
the per-season coverage flags.

Personal research only. The key is read from the API_FOOTBALL_KEY environment variable and is never
written anywhere. Raw responses are cached under data/raw/api_football/ (gitignored; never committed
or pushed). Standard library only. The app never imports this module, so it stays offline.
"""

import json
import os
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

import pandas as pd

from src.config import RAW_DIR
from src.seasons import season_label

BASE_URL = "https://v3.football.api-sports.io"
KEY_VARIABLE = "API_FOOTBALL_KEY"
CACHE_DIR = RAW_DIR / "api_football"
PREMIER_LEAGUE = 39
TIMEOUT_SECONDS = 30
FIRST_LINEUP_SEASON = 2015  # 2015-16, lookback only; the offset trains from 2016-17
LAST_LINEUP_SEASON = 2026  # 2026-27, the verdict season
COVERAGE_FLAGS = {  # report column -> path inside a season's "coverage" object
    "lineups": ("fixtures", "lineups"),
    "events": ("fixtures", "events"),
    "player_statistics": ("fixtures", "statistics_players"),
    "injuries": ("injuries",),
}


class ApiFootballError(RuntimeError):
    """A missing key or a request API-Football refused."""


def api_key(environ: Mapping[str, str] = os.environ) -> str:
    key = environ.get(KEY_VARIABLE, "").strip()
    if not key:
        raise ApiFootballError(f"set the {KEY_VARIABLE} environment variable to your API-Football key")
    return key


def request_url(endpoint: str, params: Mapping[str, object]) -> str:
    return f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(sorted(params.items()))}"


def cache_path(endpoint: str, params: Mapping[str, object], cache_dir: Path = CACHE_DIR) -> Path:
    """One file per endpoint and parameter set, e.g. leagues__id-39.json."""
    name = endpoint.replace("/", "_") + "".join(f"__{key}-{value}" for key, value in sorted(params.items()))
    return cache_dir / f"{name}.json"


def fetch(endpoint: str, params: Mapping[str, object], key: str | None = None, cache_dir: Path = CACHE_DIR,
          refresh: bool = False, opener: Callable = urllib.request.urlopen) -> dict:
    """The JSON response for an endpoint, from the cache unless `refresh`. A refused request (the
    API answers with a non-empty "errors" field for plan, key or rate problems) raises and is not
    cached."""
    path = cache_path(endpoint, params, cache_dir)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    request = urllib.request.Request(request_url(endpoint, params), headers={"x-apisports-key": key or api_key()})
    with opener(request, timeout=TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise ApiFootballError(f"API-Football refused {endpoint} {dict(params)}: {payload['errors']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def flag(coverage: Mapping[str, object], path: tuple[str, ...]) -> bool | None:
    """A coverage flag, or None if the response does not have it."""
    value: object = coverage
    for part in path:
        value = value.get(part) if isinstance(value, Mapping) else None
    return value if isinstance(value, bool) else None


def season_coverage(payload: Mapping[str, object]) -> pd.DataFrame:
    """Per season of the league in a /leagues response: its label, dates and coverage flags."""
    league = payload["response"][0]
    rows = [{"year": season["year"], "season": season_label(season["year"]), "start": season.get("start"),
             "end": season.get("end"),
             **{name: flag(season.get("coverage", {}), path) for name, path in COVERAGE_FLAGS.items()}}
            for season in league["seasons"]]
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def seasons_without_lineups(coverage: pd.DataFrame, first: int = FIRST_LINEUP_SEASON,
                            last: int = LAST_LINEUP_SEASON) -> list[str]:
    """Labels of the seasons first..last that are missing or not covered for lineups."""
    covered = set(coverage.loc[coverage["lineups"].eq(True), "year"])
    return [season_label(year) for year in range(first, last + 1) if year not in covered]
