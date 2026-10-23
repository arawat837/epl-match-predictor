"""Maps between FPL and football-data: team names, and FPL rows to our matches.

Team names: exact football-data short name, then the manual override file, then a fuzzy
match against football-data short names. Players: FPL's `code` is a persistent player id
across seasons, so no fuzzy matching is needed within FPL. Transfermarkt is not used: its
terms forbid automated access (see CLAUDE.md).
"""

import difflib
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT
from src.teams import TEAM_NAMES

OVERRIDES_PATH = PROJECT_ROOT / "data" / "manual" / "fpl_team_names.csv"
FUZZY_CUTOFF = 0.75
LINK_THRESHOLD = 0.98  # minimum minutes-weighted share of FPL rows linked to a player, team and match


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, str]:
    """Manual FPL name -> club name overrides; every target must be a known club name."""
    overrides = pd.read_csv(path)
    unknown = set(overrides["canonical"]) - set(TEAM_NAMES.values())
    if unknown:
        raise ValueError(f"override targets are not club names: {sorted(unknown)}")
    return dict(zip(overrides["fpl_name"], overrides["canonical"]))


def match_team(fpl_name: str, overrides: dict[str, str]) -> tuple[str | None, str]:
    """(club name, how it was matched) for one FPL team name."""
    if fpl_name in TEAM_NAMES:
        return TEAM_NAMES[fpl_name], "exact"
    if fpl_name in overrides:
        return overrides[fpl_name], "override"
    close = difflib.get_close_matches(fpl_name, list(TEAM_NAMES), n=1, cutoff=FUZZY_CUTOFF)
    return (TEAM_NAMES[close[0]], f"fuzzy ({close[0]})") if close else (None, "unmatched")


def team_name_map(fpl_names: list[str], overrides: dict[str, str]) -> pd.DataFrame:
    """One row per FPL team name: club name and method. Raises if any name is unmatched."""
    rows = [(name, *match_team(name, overrides)) for name in sorted(set(fpl_names))]
    table = pd.DataFrame(rows, columns=["fpl_name", "canonical", "method"])
    unmatched = table.loc[table["canonical"].isna(), "fpl_name"].tolist()
    if unmatched:
        raise ValueError(f"FPL team names with no match: {unmatched}; add them to {OVERRIDES_PATH.name}")
    return table


def kickoff_date(kickoff: pd.Series) -> pd.Series:
    """UK calendar date of a UTC kickoff, to compare with football-data dates."""
    return kickoff.dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()


def link_rows(rows: pd.DataFrame, matches: pd.DataFrame, names: dict[str, str]) -> pd.DataFrame:
    """FPL rows with club names for the player's team and both sides, and the football-data
    match date (by season, home and away). Unlinked rows keep a missing date."""
    linked = rows.assign(team=rows["fpl_team"].map(names), home=rows["fpl_home"].map(names),
                         away=rows["fpl_away"].map(names))
    keys = matches[["season", "home", "away", "date"]]
    return linked.merge(keys, on=["season", "home", "away"], how="left", validate="many_to_one")


def is_linked(linked: pd.DataFrame) -> pd.Series:
    """Rows with a persistent player id, a club and a football-data match."""
    return linked["player"].notna() & linked["team"].notna() & linked["date"].notna()


def minutes_weighted_link_rate(linked: pd.DataFrame) -> float:
    """Share of all FPL minutes played in rows that link to a player, team and match."""
    return float(linked.loc[is_linked(linked), "minutes"].sum() / linked["minutes"].sum())


def check_link_rate(rate: float, threshold: float = LINK_THRESHOLD) -> None:
    """Fail loudly when too few minutes link."""
    if rate < threshold:
        raise ValueError(f"only {rate:.2%} of FPL minutes link to a player, team and match (need {threshold:.0%})")
