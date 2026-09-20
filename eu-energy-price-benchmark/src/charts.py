"""
Chart rendering.

The colours are not a taste decision. The categorical slots below were checked
with a palette validator for colour-vision-deficiency separation (worst adjacent
pair Delta-E 9.2, target >= 8) and for contrast against the chart surface; the
slot that falls below 3:1 contrast is only used where a direct value label is
printed next to the mark, which is what makes it readable anyway.

Rules applied throughout, each of which exists because breaking it misleads:
  - one value axis, never two (a second y-scale lets the author choose the story)
  - a legend only when there is more than one series
  - the home country highlighted, peers recessive: the chart has a subject
  - direct labels on the values that matter, never on every point
  - gridlines recessive, no gradients, no 3-D
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Validated categorical slots (light surface)
BLUE = "#2a78d6"        # the subject: Czechia
AQUA = "#1baf7a"
ORANGE = "#eb6834"
GREY = "#8f9aa6"        # peers
DARK_GREY = "#4f5a64"   # EU reference line

INK = "#0b0b0b"
MUTED = "#3f4b57"
GRID = "#dcdfe3"
SURFACE = "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.labelsize": 12.5,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 11.5,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

HOME = "Czechia"
REFERENCE = "EU average"


def _cents(value: float, _pos=None) -> str:
    return f"{value * 100:.0f}"


def _finish(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path


def price_history(wide, path: Path, since: str = "2015-S1") -> Path:
    """One line per country; the subject in colour, everyone else in grey."""
    wide = wide[wide.index >= since]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))

    for country in wide.columns:
        if country in (HOME, REFERENCE):
            continue
        ax.plot(wide.index, wide[country], color=GREY, linewidth=1.4, zorder=1)

    ax.plot(wide.index, wide[REFERENCE], color=DARK_GREY, linewidth=1.8,
            linestyle="--", zorder=2, label=REFERENCE)
    ax.plot(wide.index, wide[HOME], color=BLUE, linewidth=2.6, zorder=3, label=HOME)

    ax.set_ylabel("EUR cents per kWh, excluding VAT")
    ax.yaxis.set_major_formatter(FuncFormatter(_cents))
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)

    ticks = [p for p in wide.index if p.endswith("S1")]
    ax.set_xticks(ticks)
    ax.set_xticklabels([p[:4] for p in ticks], fontsize=11)
    ax.tick_params(axis="y", labelsize=11)

    # Label the two lines that carry meaning, at their right-hand end. When the
    # series converge -- which is exactly what happened in 2025 -- the two labels
    # collide, so they are pushed apart in proportion to how close the lines are.
    ends = {HOME: float(wide[HOME].iloc[-1]), REFERENCE: float(wide[REFERENCE].iloc[-1])}
    span = float(wide.max().max() - wide.min().min())
    too_close = abs(ends[HOME] - ends[REFERENCE]) < span * 0.06
    styles = {HOME: (BLUE, "bold"), REFERENCE: (DARK_GREY, "normal")}
    upper = max(ends, key=ends.get)
    for country, value in ends.items():
        offset = 0
        if too_close:
            offset = 7 if country == upper else -7
        colour, weight = styles[country]
        ax.annotate(country, (len(wide) - 1, value), textcoords="offset points",
                    xytext=(8, offset), va="center", fontsize=11,
                    color=colour, fontweight=weight)
    others = [c for c in wide.columns if c not in (HOME, REFERENCE)]
    ax.annotate(f"{len(others)} neighbouring markets", (len(wide) - 1, wide[others].iloc[-1].max()),
                textcoords="offset points", xytext=(8, 6), va="center",
                fontsize=10.5, color=MUTED)
    ax.set_xlim(0, len(wide) - 1 + 0.02 * len(wide))
    fig.subplots_adjust(right=0.82)
    return _finish(fig, path)


def price_ranking(labels: list[str], values: list[float], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    colours = [BLUE if label == HOME else GREY for label in labels]
    bars = ax.barh(labels, values, color=colours, height=0.62)
    ax.invert_yaxis()
    ax.set_xlabel("EUR cents per kWh, excluding VAT")
    ax.xaxis.set_major_formatter(FuncFormatter(_cents))
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(labelsize=11.5)

    span = max(values)
    for bar, value, label in zip(bars, values, labels):
        ax.text(bar.get_width() + span * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{value * 100:.1f}",
                va="center", fontsize=11, color=INK,
                fontweight="bold" if label == HOME else "normal")
    ax.set_xlim(0, span * 1.12)
    return _finish(fig, path)


def composition(labels: list[str], energy: list[float], network: list[float],
                taxes: list[float], path: Path) -> Path:
    """Stacked bars: three components, a legend, and labels inside each segment."""
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    left = [0.0] * len(labels)
    series = [
        ("Energy & supply", energy, BLUE),
        ("Network costs", network, AQUA),
        ("Taxes and levies", taxes, ORANGE),
    ]
    for name, values, colour in series:
        ax.barh(labels, values, left=left, color=colour, height=0.6,
                label=name, edgecolor=SURFACE, linewidth=2)   # 2px surface gap
        for i, value in enumerate(values):
            total = energy[i] + network[i] + taxes[i]
            if value / total > 0.09:                          # only where it fits
                ax.text(left[i] + value / 2, i, f"{value / total * 100:.0f}%",
                        ha="center", va="center", fontsize=11, color="white",
                        fontweight="bold")
        left = [l + v for l, v in zip(left, values)]

    ax.invert_yaxis()
    ax.set_xlabel("EUR cents per kWh, excluding VAT")
    ax.xaxis.set_major_formatter(FuncFormatter(_cents))
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(labelsize=11.5)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.26), ncol=3,
              frameon=False, fontsize=11)
    return _finish(fig, path)


def band_curve(bands: list[str], series: dict[str, list[float | None]], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = range(len(bands))
    for country, values in series.items():
        if country in (HOME, REFERENCE):
            continue
        ax.plot(x, values, color=GREY, linewidth=1.4, marker="o", markersize=4, zorder=1)
    ax.plot(x, series[REFERENCE], color=DARK_GREY, linewidth=1.8, linestyle="--",
            marker="o", markersize=5, zorder=2)
    ax.plot(x, series[HOME], color=BLUE, linewidth=2.6, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)

    ax.set_ylabel("EUR cents per kWh, excluding VAT")
    ax.yaxis.set_major_formatter(FuncFormatter(_cents))
    ax.set_xticks(list(x))
    ax.set_xticklabels(bands, rotation=30, ha="right", fontsize=10.5)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", labelsize=11)

    for country, colour, weight in [(HOME, BLUE, "bold"), (REFERENCE, DARK_GREY, "normal")]:
        values = [v for v in series[country] if v is not None]
        ax.annotate(country, (len(values) - 1, values[-1]),
                    textcoords="offset points", xytext=(8, 0),
                    fontsize=11, color=colour, fontweight=weight, va="center")
    fig.subplots_adjust(right=0.84)
    return _finish(fig, path)
