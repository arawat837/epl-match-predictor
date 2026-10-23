"""vaastav/Fantasy-Premier-League archive: download once, cache, and load per season.

Only evaluation seasons are fetched; the holdout season and later are never downloaded.
"""

import sys
from pathlib import Path
from urllib.error import HTTPError

import pandas as pd

from src.config import FIRST_TEST_SEASON, HOLDOUT_SEASON, RAW_DIR
from src.data import fetch_csv, write_atomic
from src.seasons import season_label, season_start

ARCHIVE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{path}"
FPL_DIR = RAW_DIR / "fpl"
SEASON_FILES = ["gws/merged_gw.csv", "players_raw.csv", "teams.csv", "fixtures.csv"]
SHARED_FILES = ["master_team_list.csv"]
MISSING_MARKER = ".missing"  # cached record that the archive has no such file


def audit_seasons() -> list[str]:
    """Seasons the audit covers: the first walk-forward test season up to the holdout."""
    return [season_label(year) for year in range(season_start(FIRST_TEST_SEASON), season_start(HOLDOUT_SEASON))]


def cache_path(path: str, fpl_dir: Path = FPL_DIR) -> Path:
    """Local copy of an archive file, e.g. 2016-17/gws/merged_gw.csv."""
    return fpl_dir / path


def fetch_once(path: str, fpl_dir: Path = FPL_DIR) -> Path | None:
    """Download an archive file unless cached; a 404 is cached too, so nothing is fetched twice."""
    local, missing = cache_path(path, fpl_dir), cache_path(path + MISSING_MARKER, fpl_dir)
    if local.exists():
        return local
    if missing.exists():
        return None
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_atomic(local, fetch_csv(ARCHIVE_URL.format(path=path)))
    except HTTPError as error:
        if error.code != 404:
            raise
        missing.touch()
        print(f"not in archive: {path}", file=sys.stderr)
        return None
    return local


def download_fpl(seasons: list[str] | None = None, fpl_dir: Path = FPL_DIR) -> dict[str, Path | None]:
    """Fetch every season file and shared file once; returns {archive path: local path or None}."""
    seasons = seasons if seasons is not None else audit_seasons()
    if any(season >= HOLDOUT_SEASON for season in seasons):
        raise ValueError(f"FPL data for {HOLDOUT_SEASON} and later is off limits")
    paths = [f"{season}/{file}" for season in seasons for file in SEASON_FILES] + SHARED_FILES
    return {path: fetch_once(path, fpl_dir) for path in paths}


def read_archive_csv(path: Path, **options: object) -> pd.DataFrame:
    """Read an archive CSV (some seasons are latin-1 encoded)."""
    try:
        return pd.read_csv(path, encoding="utf-8", **options)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **options)


# Columns read from gameweek files. xP is deliberately absent: it is never read (look-ahead bias).
GW_COLUMNS = ["element", "fixture", "kickoff_time", "round", "was_home", "opponent_team", "minutes",
              "starts", "yellow_cards", "red_cards", "bps", "ict_index", "value", "team", "position"]
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def read_gameweeks(path: Path) -> pd.DataFrame:
    """Per-player per-fixture rows, only GW_COLUMNS."""
    rows = read_archive_csv(path, usecols=lambda column: column in GW_COLUMNS, low_memory=False)
    return rows.assign(was_home=rows["was_home"].astype(str).str.lower().eq("true"))


def fixture_sides(gameweeks: pd.DataFrame) -> pd.DataFrame:
    """Each fixture's home and away FPL team ids: a home row's opponent is the away side."""
    def side(rows: pd.DataFrame) -> pd.Series:
        return rows.groupby("fixture")["opponent_team"].agg(lambda ids: ids.mode().iloc[0])
    return pd.DataFrame({"home_id": side(gameweeks[~gameweeks["was_home"]]),
                         "away_id": side(gameweeks[gameweeks["was_home"]])}).reset_index()


def team_names(season: str, fpl_dir: Path = FPL_DIR) -> dict[int, str]:
    """FPL team id -> FPL team name for a season (teams.csv, else master_team_list.csv)."""
    teams = cache_path(f"{season}/teams.csv", fpl_dir)
    if teams.exists():
        frame = read_archive_csv(teams)
        return dict(zip(frame["id"], frame["name"]))
    master = read_archive_csv(cache_path("master_team_list.csv", fpl_dir))
    master = master[master["season"] == season]
    return dict(zip(master["team"], master["team_name"]))


def optional(rows: pd.DataFrame, column: str) -> pd.Series:
    """A column the season may not have, as all-missing when absent."""
    return rows[column] if column in rows else pd.Series(pd.NA, index=rows.index)


def load_season(season: str, fpl_dir: Path = FPL_DIR) -> pd.DataFrame:
    """One season's FPL rows in a standard shape: the player's persistent `code`, his team
    for that fixture (derived from the fixture's sides), both sides' FPL names, and the stats."""
    gameweeks = read_gameweeks(cache_path(f"{season}/gws/merged_gw.csv", fpl_dir))
    players = read_archive_csv(cache_path(f"{season}/players_raw.csv", fpl_dir), usecols=["id", "code", "element_type"])
    rows = gameweeks.merge(fixture_sides(gameweeks), on="fixture", how="left").merge(
        players.rename(columns={"id": "element"}), on="element", how="left")
    names = team_names(season, fpl_dir)
    return pd.DataFrame({
        "season": season, "fixture": rows["fixture"], "round": rows["round"],
        "kickoff": pd.to_datetime(rows["kickoff_time"], utc=True),
        "element": rows["element"], "player": rows["code"],
        "fpl_team": rows["home_id"].where(rows["was_home"], rows["away_id"]).map(names),
        "fpl_home": rows["home_id"].map(names), "fpl_away": rows["away_id"].map(names),
        "recorded_team": optional(rows, "team"), "was_home": rows["was_home"],
        "position": rows["element_type"].map(POSITIONS), "recorded_position": optional(rows, "position"),
        "minutes": rows["minutes"], "starts": optional(rows, "starts"),
        "yellow_cards": rows["yellow_cards"], "red_cards": rows["red_cards"],
        "bps": rows["bps"], "ict_index": rows["ict_index"], "price": rows["value"] / 10,
    })


def load_fpl(seasons: list[str] | None = None, fpl_dir: Path = FPL_DIR) -> pd.DataFrame:
    """Every cached season's rows, stacked."""
    seasons = seasons if seasons is not None else audit_seasons()
    present = [season for season in seasons if cache_path(f"{season}/gws/merged_gw.csv", fpl_dir).exists()]
    return pd.concat([load_season(season, fpl_dir) for season in present], ignore_index=True)
