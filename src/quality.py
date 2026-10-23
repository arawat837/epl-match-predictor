"""Data-quality checks and report for the match table.

These are integrity checks only (counts, gaps, duplicates, dates); they never look
at outcomes, so running them over the holdout season reveals nothing about it.
"""

import pandas as pd

from src.config import MATCHES_PER_SEASON
from src.seasons import season_start

TEAMS_PER_SEASON = 20


def rows_per_season(matches: pd.DataFrame, in_progress: str | None) -> pd.DataFrame:
    """Rows and teams per season. Complete seasons need 380 rows and 20 teams;
    the in-progress season only needs to stay within those limits."""
    summary = matches.groupby("season").agg(rows=("home", "size"), teams=("home", "nunique"))
    summary["complete"] = summary.index != in_progress
    exact = (summary["rows"] == MATCHES_PER_SEASON) & (summary["teams"] == TEAMS_PER_SEASON)
    within = (summary["rows"] <= MATCHES_PER_SEASON) & (summary["teams"] <= TEAMS_PER_SEASON)
    summary["ok"] = exact.where(summary["complete"], within)
    return summary.reset_index()


def missing_values(matches: pd.DataFrame) -> pd.DataFrame:
    """Missing cells per season, for columns that have any."""
    missing = matches.isna().groupby(matches["season"]).sum()
    return missing.loc[missing.sum(axis=1) > 0, missing.sum() > 0]


def duplicate_fixtures(matches: pd.DataFrame) -> pd.DataFrame:
    """Rows whose (season, home, away) appears more than once."""
    return matches[matches.duplicated(subset=["season", "home", "away"], keep=False)]


def double_bookings(matches: pd.DataFrame) -> pd.DataFrame:
    """(date, team) pairs where a team has more than one match on the same date."""
    appearances = pd.concat([
        matches[["date", "home"]].rename(columns={"home": "team"}),
        matches[["date", "away"]].rename(columns={"away": "team"}),
    ])
    clashes = appearances[appearances.duplicated(keep=False)]
    return clashes.drop_duplicates().sort_values(["date", "team"], ignore_index=True)


def dates_outside_season(matches: pd.DataFrame) -> pd.DataFrame:
    """Matches dated outside 1 July of the start year to 31 July of the end year."""
    start = matches["season"].map(season_start)
    opens = pd.to_datetime(start.astype(str) + "-07-01")
    closes = pd.to_datetime((start + 1).astype(str) + "-07-31")
    return matches[(matches["date"] < opens) | (matches["date"] > closes)]


def failed_checks(matches: pd.DataFrame, in_progress: str | None) -> list[str]:
    """Names of the checks that fail; empty when the table is clean."""
    failures = {
        "rows per season": not rows_per_season(matches, in_progress)["ok"].all(),
        "missing values": not missing_values(matches).empty,
        "duplicate fixtures": not duplicate_fixtures(matches).empty,
        "double bookings": not double_bookings(matches).empty,
        "dates outside season": not dates_outside_season(matches).empty,
    }
    return [name for name, failed in failures.items() if failed]


def section(title: str, table: pd.DataFrame) -> str:
    """One report section: a count line, plus the offending rows if there are any."""
    if table.empty:
        return f"{title}: none"
    return f"{title}: {len(table)}\n{table.to_string()}"


def quality_report(matches: pd.DataFrame, in_progress: str | None) -> str:
    """Human-readable data-quality report."""
    seasons = sorted(matches["season"].unique())
    failures = failed_checks(matches, in_progress)
    lines = [
        f"Data-quality report: {len(matches)} matches, {seasons[0]} to {seasons[-1]}",
        f"In-progress season (not expected complete): {in_progress}",
        "",
        f"Rows per season (complete seasons expect {MATCHES_PER_SEASON} rows, {TEAMS_PER_SEASON} teams)",
        rows_per_season(matches, in_progress).to_string(index=False),
        "",
        section("Seasons with missing values", missing_values(matches)),
        section("Duplicate fixtures (same season, home, away)", duplicate_fixtures(matches)),
        section("Teams with two matches on one date", double_bookings(matches)),
        section("Matches dated outside their season", dates_outside_season(matches)),
        "",
        f"FAILED: {', '.join(failures)}" if failures else "All checks passed.",
    ]
    return "\n".join(lines)
