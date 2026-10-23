import pandas as pd

from src.plots import plot_importance


def test_importance_plot_is_written_as_png(tmp_path):
    importance = pd.Series({f"feature_{i}": 1 / (i + 1) for i in range(20)})
    path = plot_importance(importance, tmp_path / "importance.png", title="t", subtitle="s")
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
