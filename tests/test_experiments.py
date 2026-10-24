"""Stage 8 windows, base probabilities and the decision rule."""

import pandas as pd
import pytest

import src.experiments as experiments
from src.config import FEATURES_PATH, MATCHES_PATH
from src.dataset import load_model_table
from src.experiments import FIRST_BASE_SEASON, Scored, Window, decision, experiment_folds
from src.metrics import OUTCOMES
from src.splits import load_evaluation_matches
from src.tuning import with_elo

needs_data = pytest.mark.skipif(not (MATCHES_PATH.exists() and FEATURES_PATH.exists()),
                                reason="run the data and feature builds first")


@needs_data
def test_base_probabilities_for_each_season_come_from_earlier_seasons_only(monkeypatch):
    seen: list[tuple[str, set[str]]] = []

    def spy(self, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        seen.append((test["season"].iloc[0], set(train["season"])))
        return pd.DataFrame(1 / 3, index=test.index, columns=OUTCOMES)

    monkeypatch.setattr(experiments.LogisticModel, "__call__", spy)
    table = with_elo(load_model_table(), load_evaluation_matches(), experiments.BASE_ELO)
    base = experiments.base_probabilities(table)
    assert seen[0][0] == FIRST_BASE_SEASON and len(seen) == 9
    assert all(season not in trained and max(trained) < season for season, trained in seen)
    assert set(table.loc[base.index, "season"]) == {season for season, _ in seen}


@needs_data
def test_training_window_for_each_season_starts_in_2016_17_and_never_includes_it():
    table = with_elo(load_model_table(), load_evaluation_matches(), experiments.BASE_ELO)
    data = table[table["season"] >= FIRST_BASE_SEASON]
    tuning, reporting = experiment_folds(data)
    assert [fold.season for fold in tuning] == ["2017-18", "2018-19", "2019-20"]
    assert [fold.season for fold in reporting] == ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
    for fold in tuning + reporting:
        trained = set(fold.train["season"])
        assert fold.season not in trained and min(trained) == FIRST_BASE_SEASON
        assert fold.train["date"].max() < fold.test["date"].min()


def scored(name: str, tuning_losses: dict[str, float], reporting_losses: dict[str, float]) -> Scored:
    """Each season gets two matches with the given per-match log loss."""
    def window(losses: dict[str, float]) -> Window:
        index = [f"{season}-{i}" for season in losses for i in range(2)]
        return Window(pd.DataFrame(), pd.Series([loss for loss in losses.values() for _ in range(2)], index=index))
    return Scored(name, window(tuning_losses), window(reporting_losses))


def seasons_of(*results: Scored) -> pd.Series:
    index = [label for result in results for window in (result.tuning, result.reporting) for label in window.losses.index]
    return pd.Series([label[:7] for label in index], index=index)


def test_decision_needs_tuning_reporting_and_three_reporting_seasons():
    base = scored("base", {"2017-18": 1.0}, {s: 1.0 for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]})
    good = scored("good", {"2017-18": 0.9}, {"2020-21": 0.9, "2021-22": 0.9, "2022-23": 0.9, "2023-24": 1.1, "2024-25": 1.05})
    two_wins = scored("two", {"2017-18": 0.9}, {"2020-21": 0.5, "2021-22": 0.9, "2022-23": 1.1, "2023-24": 1.1, "2024-25": 1.1})
    worse_tuning = scored("tune", {"2017-18": 1.1}, {s: 0.9 for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]})
    seasons = seasons_of(base)
    assert decision(good, base, seasons)["decision"] == "adopted"
    assert decision(two_wins, base, seasons)["decision"] == "not adopted"  # pooled better, only 2 of 5 seasons
    assert decision(worse_tuning, base, seasons)["decision"] == "not adopted"
