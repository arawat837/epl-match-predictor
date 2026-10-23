import pytest

from src.data import MATCH_COLUMNS
from src.dataset import join_features, load_model_table, model_feature_columns
from src.features import build_features, save_features


def test_join_attaches_each_matchs_features_one_to_one(make_seasons):
    matches = make_seasons([2005, 2006])
    table = join_features(matches, build_features(matches))
    assert len(table) == len(matches)
    assert "elo_diff" in table.columns and "burn_in" in table.columns


def test_join_raises_when_features_are_stale(make_seasons):
    matches = make_seasons([2005, 2006])
    with pytest.raises(ValueError, match="no features"):
        join_features(matches, build_features(matches).iloc[:-1])


def test_model_table_drops_burn_in_and_inputs_exclude_match_columns(make_seasons, tmp_path):
    matches = make_seasons([2005, 2006])
    matches.to_parquet(tmp_path / "matches.parquet", index=False)
    save_features(build_features(matches), tmp_path / "features.parquet")
    table = load_model_table(tmp_path / "matches.parquet", tmp_path / "features.parquet")
    assert set(table["season"]) == {"2006-07"}
    assert set(model_feature_columns(table)).isdisjoint([*MATCH_COLUMNS, "burn_in"])
