"""Report figures, drawn with matplotlib's object API (no pyplot, no display needed)."""

from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"
SERIES_1 = "#2a78d6"


def plot_importance(importance: pd.Series, path: Path, title: str, subtitle: str, top: int = 15) -> Path:
    """Horizontal bars of the `top` largest importances, largest first, share printed at each tip."""
    shown = importance.head(top).iloc[::-1]
    figure = Figure(figsize=(8, 6.2), dpi=150, facecolor=SURFACE)
    axes = figure.add_axes((0.36, 0.08, 0.58, 0.78), facecolor=SURFACE)
    axes.barh(shown.index, shown.to_numpy(), height=0.4, color=SERIES_1, zorder=2)
    for position, value in enumerate(shown.to_numpy()):
        axes.text(value + shown.max() * 0.01, position, f"{value:.1%}", va="center",
                  fontsize=8, color=TEXT_SECONDARY)
    axes.set_xlim(0, shown.max() * 1.15)
    axes.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    axes.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    axes.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)
    axes.tick_params(axis="y", labelcolor=TEXT_PRIMARY)
    for spine in axes.spines.values():
        spine.set_visible(False)
    figure.text(0.03, 0.95, title, fontsize=12, weight="bold", color=TEXT_PRIMARY)
    figure.text(0.03, 0.915, subtitle, fontsize=9, color=TEXT_SECONDARY)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, facecolor=SURFACE)
    return path
