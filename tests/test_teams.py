import pandas as pd
import pytest

from src.teams import standardise_team_names


def test_short_names_map_to_full_names():
    raw = pd.Series(["Man United", " Wolves", "Nott'm Forest"])
    assert standardise_team_names(raw).tolist() == [
        "Manchester United", "Wolverhampton Wanderers", "Nottingham Forest",
    ]


def test_unknown_name_raises():
    with pytest.raises(ValueError, match="Gotham FC"):
        standardise_team_names(pd.Series(["Arsenal", "Gotham FC"]))


def test_missing_name_stays_missing():
    assert standardise_team_names(pd.Series(["Arsenal", None])).isna().tolist() == [False, True]
