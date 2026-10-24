from dataclasses import fields

from src.config import FIRST_REPORTING_SEASON, FIRST_TEST_SEASON, HOLDOUT_SEASON
from src.elo import EloParams
from src.experiments import BASE_C, BASE_ELO
from src.final_model import elo_params, load_config, predictor
from src.models import MAX_ITER
from src.seasons import season_label, season_start
from src.tuning import COMPACT_FEATURES


def seasons_between(first: str, before: str) -> list[str]:
    return [season_label(year) for year in range(season_start(first), season_start(before))]


def test_config_loads_and_matches_the_code_defaults():
    config = load_config()
    assert elo_params(config) == BASE_ELO
    assert set(config["elo"]) == {field.name for field in fields(EloParams)}
    assert config["features"] == COMPACT_FEATURES
    assert config["model"]["C"] == BASE_C
    assert config["model"]["max_iter"] == MAX_ITER
    assert config["holdout_season"] == HOLDOUT_SEASON
    assert config["tuning_seasons"] == seasons_between(FIRST_TEST_SEASON, FIRST_REPORTING_SEASON)
    assert config["reporting_seasons"] == seasons_between(FIRST_REPORTING_SEASON, HOLDOUT_SEASON)


def test_predictor_is_built_from_the_config():
    model = predictor(load_config())
    assert model.columns == COMPACT_FEATURES and model.C == BASE_C
