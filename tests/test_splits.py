import pytest

from src.splits import HoldoutLockedError, load_evaluation_matches, walk_forward_splits


def test_folds_run_from_first_test_season_to_last_season_present(make_seasons):
    folds = list(walk_forward_splits(make_seasons(range(2012, 2018)), first_test_season="2015-16"))
    assert [fold.season for fold in folds] == ["2015-16", "2016-17", "2017-18"]


def test_each_fold_trains_on_every_earlier_match_and_tests_on_one_season(make_seasons):
    matches = make_seasons(range(2012, 2018))
    for fold in walk_forward_splits(matches, first_test_season="2015-16"):
        assert fold.train["date"].max() < fold.test["date"].min()
        assert set(fold.test["season"]) == {fold.season}
        assert fold.train.equals(matches[matches["season"] < fold.season])


def test_locked_holdout_in_the_table_raises(make_seasons):
    with pytest.raises(HoldoutLockedError, match="2025-26"):
        list(walk_forward_splits(make_seasons([2023, 2024, 2025]), first_test_season="2024-25"))


def test_unlocked_holdout_becomes_the_last_fold(make_seasons):
    folds = walk_forward_splits(make_seasons([2023, 2024, 2025]), "2024-25", unlock_holdout=True)
    assert [fold.season for fold in folds] == ["2024-25", "2025-26"]


def test_seasons_after_the_holdout_raise_even_when_unlocked(make_seasons):
    with pytest.raises(HoldoutLockedError, match="2026-27"):
        list(walk_forward_splits(make_seasons([2024, 2025, 2026]), "2024-25", unlock_holdout=True))


def test_loading_filters_locked_seasons_at_read_time(make_seasons, tmp_path):
    path = tmp_path / "matches.parquet"
    make_seasons([2024, 2025, 2026]).to_parquet(path, index=False)
    assert set(load_evaluation_matches(path)["season"]) == {"2024-25"}
    assert set(load_evaluation_matches(path, unlock_holdout=True)["season"]) == {"2024-25", "2025-26"}
