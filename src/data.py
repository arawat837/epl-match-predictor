"""Download football-data.co.uk EPL season files and build the clean match table."""

import sys
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd

from src.config import FIRST_SEASON, MATCHES_PATH, RAW_DIR
from src.seasons import current_season, season_code, season_label, seasons_through_current
from src.teams import standardise_team_names

SEASON_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"
USER_AGENT = "epl-predictor/0.1"

COUNT_COLUMNS = ["FTHG", "FTAG", "HS", "AS", "HST", "AST"]
ODDS_COLUMNS = ["odds_home", "odds_draw", "odds_away"]
MATCH_COLUMNS = ["date", "season", "home", "away", *COUNT_COLUMNS[:2], "result",
                 *COUNT_COLUMNS[2:], *ODDS_COLUMNS, "odds_source"]
# Optional raw columns; a season without one gets it as all-missing instead of failing.
OPTIONAL_RAW_COLUMNS = ["FTR", "HS", "AS", "HST", "AST"]
# Preference order for a match's H/D/A prices: Bet365, then Pinnacle, then other
# books, then the market average (named Avg from 2019-20, BbAv before).
BOOKMAKERS = ("B365", "PS", "BW", "WH", "VC", "IW", "LB", "Avg", "BbAv")


def season_url(start_year: int) -> str:
    """Download URL for one season's Premier League file."""
    return SEASON_URL.format(code=season_code(start_year))


def raw_path(start_year: int, raw_dir: Path = RAW_DIR) -> Path:
    """Cache location for one season's raw file."""
    return raw_dir / f"E0_{season_code(start_year)}.csv"


def fetch_csv(url: str, timeout: float = 30.0) -> bytes:
    """Fetch a file's bytes over HTTP."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def write_atomic(path: Path, content: bytes) -> None:
    """Write via a temporary file so a failed download never leaves a truncated cache."""
    partial = path.with_suffix(".part")
    partial.write_bytes(content)
    partial.replace(path)


def fetch_season(start_year: int, path: Path, is_current: bool) -> bool:
    """Download one season to `path`. Returns False if the current season has no file yet."""
    try:
        write_atomic(path, fetch_csv(season_url(start_year)))
    except HTTPError as error:
        if not (is_current and error.code == 404):
            raise
        print(f"warning: no file yet for {season_label(start_year)}, skipping", file=sys.stderr)
        return False
    return True


def download_epl(
    seasons: Iterable[int] | None = None,
    raw_dir: Path = RAW_DIR,
    today: date | None = None,
) -> dict[int, Path]:
    """Cache each season's E0.csv in `raw_dir` and return {start year: path}.

    Seasons are start years (2005 = 2005-06), defaulting to 2005-06 through the
    current season. Cached files are reused, except the current season, which is
    always re-downloaded to pick up new results.
    """
    current = current_season(today)
    seasons = list(seasons) if seasons is not None else seasons_through_current(FIRST_SEASON, today)
    raw_dir.mkdir(parents=True, exist_ok=True)
    files: dict[int, Path] = {}
    for start_year in seasons:
        path = raw_path(start_year, raw_dir)
        is_current = start_year == current
        if (is_current or not path.exists()) and not fetch_season(start_year, path, is_current):
            continue
        files[start_year] = path
    return files


def read_raw_season(path: Path) -> pd.DataFrame:
    """Read a raw file as text, stripping the BOM some seasons have and dropping blank rows."""
    raw = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    return raw.dropna(how="all").reset_index(drop=True)


def add_missing_columns(raw: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add any of `columns` the season lacks, as all-missing."""
    missing = {column: pd.NA for column in columns if column not in raw.columns}
    return raw.assign(**missing)


def parse_dates(raw: pd.Series) -> pd.Series:
    """Parse day-first dates; older seasons use dd/mm/yy, newer ones dd/mm/yyyy."""
    text = raw.str.strip()
    long_years = pd.to_datetime(text.where(text.str.len() == 10), format="%d/%m/%Y")
    short_years = pd.to_datetime(text.where(text.str.len() == 8), format="%d/%m/%y")
    return long_years.fillna(short_years)


def to_counts(raw: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Integer columns (goals, shots) that allow missing values."""
    return raw[columns].apply(pd.to_numeric, errors="coerce").astype("Int64")


def derive_result(home_goals: pd.Series, away_goals: pd.Series) -> pd.Series:
    """H/D/A from full-time goals; missing if either score is missing."""
    margin = (home_goals - away_goals).astype("float64")
    result = pd.Series(pd.NA, index=margin.index, dtype="string")
    result[margin > 0] = "H"
    result[margin == 0] = "D"
    result[margin < 0] = "A"
    return result


def check_result_matches_ftr(result: pd.Series, ftr: pd.Series) -> None:
    """Raise if the file's FTR column disagrees with the result implied by the goals."""
    disagree = (result != ftr.astype("string")).fillna(False)
    if disagree.any():
        raise ValueError(f"{int(disagree.sum())} rows where FTR disagrees with FTHG/FTAG")


def bookmaker_prices(raw: pd.DataFrame, bookmaker: str) -> pd.DataFrame | None:
    """One bookmaker's H/D/A decimal odds, or None if the season doesn't carry them."""
    columns = [f"{bookmaker}{outcome}" for outcome in "HDA"]
    if not set(columns) <= set(raw.columns):
        return None
    return raw[columns].apply(pd.to_numeric, errors="coerce").astype("float64")


def select_odds(raw: pd.DataFrame) -> pd.DataFrame:
    """Per match, take H/D/A odds from the first bookmaker in BOOKMAKERS that has all three.

    The three prices always come from the same bookmaker; `odds_source` names it.
    """
    odds = pd.DataFrame(index=raw.index, columns=ODDS_COLUMNS, dtype="float64")
    source = pd.Series(pd.NA, index=raw.index, dtype="string")
    for bookmaker in BOOKMAKERS:
        prices = bookmaker_prices(raw, bookmaker)
        if prices is None:
            continue
        usable = source.isna() & prices.gt(1.0).all(axis=1)
        odds.loc[usable] = prices.loc[usable].to_numpy()
        source[usable] = bookmaker
    return odds.assign(odds_source=source)


def clean_season(raw: pd.DataFrame, start_year: int) -> pd.DataFrame:
    """Turn one raw season into the standard match table (columns MATCH_COLUMNS)."""
    raw = add_missing_columns(raw, OPTIONAL_RAW_COLUMNS)
    counts = to_counts(raw, COUNT_COLUMNS)
    result = derive_result(counts["FTHG"], counts["FTAG"])
    check_result_matches_ftr(result, raw["FTR"])
    matches = pd.DataFrame({
        "date": parse_dates(raw["Date"]),
        "season": season_label(start_year),
        "home": standardise_team_names(raw["HomeTeam"]),
        "away": standardise_team_names(raw["AwayTeam"]),
        "result": result,
    })
    return pd.concat([matches, counts, select_odds(raw)], axis=1)[MATCH_COLUMNS]


def build_matches(raw_files: Mapping[int, Path]) -> pd.DataFrame:
    """Clean every season and stack them in date order."""
    seasons = [clean_season(read_raw_season(path), start_year)
               for start_year, path in sorted(raw_files.items())]
    matches = pd.concat(seasons, ignore_index=True)
    return matches.sort_values(["date", "home"], kind="stable", ignore_index=True)


def save_matches(matches: pd.DataFrame, path: Path = MATCHES_PATH) -> Path:
    """Write the match table to parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    matches.to_parquet(path, index=False)
    return path
