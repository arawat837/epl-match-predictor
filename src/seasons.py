"""Season identifiers.

A season is identified by its start year (2025 = 2025-26). football-data.co.uk
uses a four-digit code ("2526"); reports use a label ("2025-26").
"""

from datetime import date

ROLLOVER_MONTH = 8  # a new season's file appears once it kicks off in August


def season_code(start_year: int) -> str:
    """football-data.co.uk code, e.g. 2025 -> "2526"."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def season_label(start_year: int) -> str:
    """Report label, e.g. 2025 -> "2025-26"."""
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def season_start(label: str) -> int:
    """Start year from a label, e.g. "2025-26" -> 2025."""
    return int(label.split("-")[0])


def current_season(today: date | None = None) -> int:
    """Start year of the season in progress, or the one just finished before August."""
    today = today or date.today()
    return today.year if today.month >= ROLLOVER_MONTH else today.year - 1


def seasons_through_current(first: int, today: date | None = None) -> list[int]:
    """Start years from `first` up to and including the current season."""
    return list(range(first, current_season(today) + 1))
