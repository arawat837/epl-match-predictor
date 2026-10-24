"""Shared fixtures: synthetic match tables in the clean matches.parquet format."""

from collections.abc import Callable, Iterable
from datetime import date, timedelta

import pandas as pd
import pytest

from src.data import MATCH_COLUMNS, derive_result
from src.seasons import season_label

COUNT_COLUMNS = ["FTHG", "FTAG", "HS", "AS", "HST", "AST"]
MatchRow = tuple[str, str, str, int, int]


def round_robin(teams: list[str]) -> list[list[tuple[str, str]]]:
    """Double round robin (circle method): every ordered pair once, each team once per round."""
    fixed, rotating = teams[0], teams[1:]
    first_half = []
    for _ in range(len(teams) - 1):
        lineup = [fixed, *rotating]
        first_half.append([(lineup[i], lineup[-1 - i]) for i in range(len(teams) // 2)])
        rotating = rotating[-1:] + rotating[:-1]
    return first_half + [[(away, home) for home, away in fixtures] for fixtures in first_half]


def synthetic_season(start_year: int, rounds: int = 38) -> pd.DataFrame:
    """20 teams, one round per week from 10 August, every match a 1-0 home win."""
    teams = [f"Team {i:02d}" for i in range(20)]
    kickoff = date(start_year, 8, 10)
    rows = [
        {"date": kickoff + timedelta(weeks=week), "home": home, "away": away}
        for week, fixtures in enumerate(round_robin(teams)[:rounds])
        for home, away in fixtures
    ]
    season = pd.DataFrame(rows).assign(
        date=lambda df: pd.to_datetime(df["date"]),
        season=season_label(start_year),
        FTHG=1, FTAG=0, result="H", HS=10, AS=8, HST=4, AST=3,
        odds_home=2.0, odds_draw=3.4, odds_away=3.8, odds_source="B365",
    )
    return season.astype({column: "Int64" for column in COUNT_COLUMNS})


@pytest.fixture
def two_seasons() -> pd.DataFrame:
    """A complete 2005-06 (380 matches) and an in-progress 2006-07 (7 rounds, 70 matches)."""
    return pd.concat([synthetic_season(2005), synthetic_season(2006, rounds=7)], ignore_index=True)


@pytest.fixture
def make_seasons() -> Callable[..., pd.DataFrame]:
    """Factory: synthetic seasons for the given start years, stacked in date order."""
    def make(start_years: Iterable[int], rounds: int = 2) -> pd.DataFrame:
        return pd.concat([synthetic_season(year, rounds) for year in start_years], ignore_index=True)
    return make


@pytest.fixture
def seasons_with_promotion() -> pd.DataFrame:
    """Three full synthetic seasons (2005-06 to 2007-08): Team 19 misses the middle one, in which
    Team 20 is promoted, and returns in 2007-08 after a gap of over a year."""
    middle = synthetic_season(2006).replace({"home": {"Team 19": "Team 20"}, "away": {"Team 19": "Team 20"}})
    return pd.concat([synthetic_season(2005), middle, synthetic_season(2007)], ignore_index=True)


def season_of(day: pd.Timestamp) -> str:
    """Season label for a date, with seasons turning over on 1 July."""
    return season_label(day.year if day.month >= 7 else day.year - 1)


@pytest.fixture
def make_matches() -> Callable[[list[MatchRow]], pd.DataFrame]:
    """Factory: a match table from (date, home, away, home goals, away goals) rows.

    Shots are 10 + goals and shots on target 2 + goals, so they can be checked by hand.
    """
    def make(rows: list[MatchRow]) -> pd.DataFrame:
        matches = pd.DataFrame(rows, columns=["date", "home", "away", "FTHG", "FTAG"])
        matches["date"] = pd.to_datetime(matches["date"])
        goals = matches[["FTHG", "FTAG"]].astype("Int64")
        return matches.assign(
            season=matches["date"].map(season_of),
            FTHG=goals["FTHG"], FTAG=goals["FTAG"],
            result=derive_result(goals["FTHG"], goals["FTAG"]),
            HS=goals["FTHG"] + 10, AS=goals["FTAG"] + 10, HST=goals["FTHG"] + 2, AST=goals["FTAG"] + 2,
            odds_home=2.7, odds_draw=3.3, odds_away=2.7, odds_source="B365",
        )[MATCH_COLUMNS]
    return make
