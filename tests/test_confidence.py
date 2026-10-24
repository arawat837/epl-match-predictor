import pandas as pd
import pytest

from src.confidence import (most_confident, overlap_table, per_season_table, reliability_table, subset_table,
                            top_probability)
from src.metrics import OUTCOMES
from src.plots import plot_reliability


def forecast(rows: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=OUTCOMES)


def test_most_confident_takes_the_highest_top_probabilities_in_match_order_on_ties():
    probabilities = forecast([[0.5, 0.3, 0.2], [0.7, 0.2, 0.1], [0.2, 0.2, 0.6], [0.2, 0.1, 0.7]])
    assert list(most_confident(probabilities, 0.5)) == [1, 3]
    assert top_probability(probabilities).tolist() == [0.5, 0.7, 0.6, 0.7]


def test_threshold_is_strict_and_small_cells_are_unreliable():
    probabilities = forecast([[0.5, 0.3, 0.2], [0.51, 0.29, 0.2], [0.2, 0.2, 0.6]] * 50)
    results = pd.Series(["H", "A", "A"] * 50)
    table = subset_table({"m": probabilities}, results).set_index("subset")
    assert table.loc["top probability > 0.50", "matches"] == 100  # 0.51 and 0.60, not 0.50
    assert table.loc["top probability > 0.50", "accuracy"] == pytest.approx(0.5)
    assert bool(table.loc["top probability > 0.50", "reliable"])
    assert not bool(table.loc["top probability > 0.55", "reliable"])  # 50 matches


def test_overlap_is_the_share_of_the_models_top_matches_also_in_the_bookmakers():
    model = forecast([[0.9, 0.05, 0.05], [0.8, 0.1, 0.1], [0.4, 0.3, 0.3], [0.5, 0.3, 0.2]] * 5)
    bookmaker = forecast([[0.9, 0.05, 0.05], [0.4, 0.3, 0.3], [0.8, 0.1, 0.1], [0.5, 0.3, 0.2]] * 5)
    table = overlap_table(model, bookmaker).set_index("coverage")
    assert table.loc["10%", "also_bookmaker_most_confident"] == 1.0  # both pick the first rows (0.9)
    assert table.loc["30%", "matches"] == 6


def test_per_season_table_counts_each_season():
    probabilities = forecast([[0.7, 0.2, 0.1]] * 6)
    table = per_season_table({"m": probabilities}, pd.Series(["H"] * 6), pd.Series(["2016-17"] * 4 + ["2017-18"] * 2))
    above = table[table["subset"] == "top probability > 0.65"].set_index("season")
    assert above["matches"].to_dict() == {"2016-17": 4, "2017-18": 2}
    assert not above["reliable"].any()


def test_reliability_uses_decile_bins_and_writes_a_plot(tmp_path):
    probabilities = forecast([[h, (1 - h) / 2, (1 - h) / 2] for h in [i / 1000 for i in range(1, 1000)]])
    results = pd.Series(["H" if i % 2 else "A" for i in range(999)])
    table = reliability_table(probabilities, results)
    home = table[table["outcome"] == "H"]
    assert len(home) == 10 and home["matches"].sum() == 999
    assert home["predicted"].is_monotonic_increasing
    path = plot_reliability(table, tmp_path / "reliability.png", title="t", subtitle="s")
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
