"""Team-name standardisation from football-data.co.uk short names to full club names."""

import pandas as pd

TEAM_NAMES: dict[str, str] = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Birmingham": "Birmingham City",
    "Blackburn": "Blackburn Rovers",
    "Blackpool": "Blackpool",
    "Bolton": "Bolton Wanderers",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton": "Brighton & Hove Albion",
    "Burnley": "Burnley",
    "Cardiff": "Cardiff City",
    "Charlton": "Charlton Athletic",
    "Chelsea": "Chelsea",
    "Coventry": "Coventry City",
    "Crystal Palace": "Crystal Palace",
    "Derby": "Derby County",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Huddersfield": "Huddersfield Town",
    "Hull": "Hull City",
    "Ipswich": "Ipswich Town",
    "Leeds": "Leeds United",
    "Leicester": "Leicester City",
    "Liverpool": "Liverpool",
    "Luton": "Luton Town",
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Middlesbrough": "Middlesbrough",
    "Newcastle": "Newcastle United",
    "Norwich": "Norwich City",
    "Nott'm Forest": "Nottingham Forest",
    "Portsmouth": "Portsmouth",
    "QPR": "Queens Park Rangers",
    "Reading": "Reading",
    "Sheffield United": "Sheffield United",
    "Southampton": "Southampton",
    "Stoke": "Stoke City",
    "Sunderland": "Sunderland",
    "Swansea": "Swansea City",
    "Tottenham": "Tottenham Hotspur",
    "Watford": "Watford",
    "West Brom": "West Bromwich Albion",
    "West Ham": "West Ham United",
    "Wigan": "Wigan Athletic",
    "Wolves": "Wolverhampton Wanderers",
}


def standardise_team_names(names: pd.Series) -> pd.Series:
    """Map raw names to full club names. Raises on any name not in TEAM_NAMES; missing stays missing."""
    stripped = names.str.strip()
    unknown = sorted(set(stripped.dropna()) - TEAM_NAMES.keys())
    if unknown:
        raise ValueError(f"Unknown team names {unknown}; add them to TEAM_NAMES in src/teams.py")
    return stripped.map(TEAM_NAMES)
