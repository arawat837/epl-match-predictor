import pandas as pd
import pytest

from src.name_maps import check_link_rate, kickoff_date, load_overrides, team_name_map

# Every FPL team name in the 2016-17 to 2024-25 archive and the club it must map to.
EXPECTED = {
    "Arsenal": "Arsenal", "Aston Villa": "Aston Villa", "Bournemouth": "Bournemouth",
    "Brentford": "Brentford", "Brighton": "Brighton & Hove Albion", "Burnley": "Burnley",
    "Cardiff": "Cardiff City", "Chelsea": "Chelsea", "Crystal Palace": "Crystal Palace",
    "Everton": "Everton", "Fulham": "Fulham", "Huddersfield": "Huddersfield Town", "Hull": "Hull City",
    "Ipswich": "Ipswich Town", "Leeds": "Leeds United", "Leicester": "Leicester City",
    "Liverpool": "Liverpool", "Luton": "Luton Town", "Man City": "Manchester City",
    "Man Utd": "Manchester United", "Middlesbrough": "Middlesbrough", "Newcastle": "Newcastle United",
    "Norwich": "Norwich City", "Nott'm Forest": "Nottingham Forest", "Sheffield Utd": "Sheffield United",
    "Southampton": "Southampton", "Spurs": "Tottenham Hotspur", "Stoke": "Stoke City",
    "Sunderland": "Sunderland", "Swansea": "Swansea City", "Watford": "Watford",
    "West Brom": "West Bromwich Albion", "West Ham": "West Ham United", "Wolves": "Wolverhampton Wanderers",
}


def test_every_fpl_team_name_maps_to_the_right_club():
    table = team_name_map(list(EXPECTED), load_overrides())
    assert dict(zip(table["fpl_name"], table["canonical"])) == EXPECTED
    methods = dict(zip(table["fpl_name"], table["method"]))
    assert methods["Spurs"] == "override"
    assert methods["Man Utd"].startswith("fuzzy")


def test_unmatched_name_fails_loudly():
    with pytest.raises(ValueError, match="no match"):
        team_name_map(["Gotham Rovers"], {})


def test_override_targets_must_be_club_names(tmp_path):
    path = tmp_path / "overrides.csv"
    path.write_text("fpl_name,canonical\nSpurs,Spurs FC\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not club names"):
        load_overrides(path)


def test_link_rate_below_98_percent_fails_loudly():
    check_link_rate(0.981)
    with pytest.raises(ValueError, match="only 97.90%"):
        check_link_rate(0.979)


def test_kickoff_date_is_the_uk_calendar_date():
    kickoffs = pd.Series(pd.to_datetime(["2019-08-10T23:30:00Z", "2020-01-01T23:30:00Z"], utc=True))
    assert kickoff_date(kickoffs).tolist() == [pd.Timestamp("2019-08-11"), pd.Timestamp("2020-01-01")]
