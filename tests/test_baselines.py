import pandas as pd
import pytest

from src.baselines import always_home, base_rate, bookmaker, uniform


@pytest.fixture
def season_matches(make_seasons) -> pd.DataFrame:
    return make_seasons([2015]).set_index(pd.RangeIndex(100, 120))


def test_constant_baselines_cover_every_test_match(season_matches):
    assert uniform(season_matches, season_matches).index.equals(season_matches.index)
    assert (uniform(season_matches, season_matches) == 1 / 3).all().all()
    assert always_home(season_matches, season_matches).drop_duplicates().values.tolist() == [[1.0, 0.0, 0.0]]


def test_base_rate_is_training_outcome_frequencies(season_matches):
    train = pd.DataFrame({"result": ["H", "H", "D", "A"]})
    forecast = base_rate(train, season_matches)
    assert forecast.index.equals(season_matches.index)
    assert forecast.drop_duplicates().values.tolist() == [[0.5, 0.25, 0.25]]


def test_base_rate_gives_zero_to_an_outcome_never_seen_in_training(season_matches):
    train = pd.DataFrame({"result": ["H", "A"]})
    assert base_rate(train, season_matches).iloc[0].tolist() == [0.5, 0.0, 0.5]


def test_bookmaker_uses_each_test_matchs_own_odds(season_matches):
    priced = season_matches.assign(odds_home=[2.0] * 10 + [4.0] * 10, odds_draw=4.0, odds_away=[4.0] * 10 + [2.0] * 10)
    forecast = bookmaker(priced.iloc[:0], priced)
    assert forecast.iloc[0].tolist() == [0.5, 0.25, 0.25]
    assert forecast.iloc[-1].tolist() == [0.25, 0.25, 0.5]
