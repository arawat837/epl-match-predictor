"""Shared fixtures: synthetic match tables in the clean matches.parquet format."""

from datetime import date, timedelta

import pandas as pd
import pytest

from src.seasons import season_label

COUNT_COLUMNS = ["FTHG", "FTAG", "HS", "AS", "HST", "AST"]


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
