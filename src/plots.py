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


OUTCOME_TITLES = {"H": "Home win", "D": "Draw", "A": "Away win"}


def plot_reliability(table: pd.DataFrame, path: Path, title: str, subtitle: str) -> Path:
    """One panel per outcome: observed frequency against mean predicted probability per decile,
    with the diagonal of perfect calibration."""
    figure = Figure(figsize=(11, 4.4), dpi=150, facecolor=SURFACE)
    for position, (outcome, label) in enumerate(OUTCOME_TITLES.items()):
        rows = table[table["outcome"] == outcome]
        axes = figure.add_axes((0.06 + position * 0.32, 0.13, 0.26, 0.64), facecolor=SURFACE)
        limit = max(rows["predicted"].max(), rows["observed"].max()) * 1.08
        axes.plot([0, limit], [0, limit], color=TEXT_SECONDARY, linewidth=1, alpha=0.6, zorder=1)
        axes.plot(rows["predicted"], rows["observed"], color=SERIES_1, linewidth=2, marker="o", markersize=6,
                  markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
        axes.set_xlim(0, limit)
        axes.set_ylim(0, limit)
        axes.set_aspect("equal")
        axes.grid(color=GRID, linewidth=0.8, zorder=0)
        axes.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)
        for spine in axes.spines.values():
            spine.set_visible(False)
        axes.set_title(label, fontsize=10, color=TEXT_PRIMARY, loc="left")
        axes.set_xlabel("mean predicted probability", fontsize=8, color=TEXT_SECONDARY)
        if position == 0:
            axes.set_ylabel("observed frequency", fontsize=8, color=TEXT_SECONDARY)
    figure.text(0.03, 0.93, title, fontsize=12, weight="bold", color=TEXT_PRIMARY)
    figure.text(0.03, 0.875, subtitle, fontsize=9, color=TEXT_SECONDARY)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, facecolor=SURFACE)
    return path
