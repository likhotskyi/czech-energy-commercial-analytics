"""
Chart rendering.

The palette slots were checked with a colour-vision-deficiency validator and for
contrast against the chart surface. Rules kept throughout: one value axis (never
two), a legend only where more than one series needs naming, the subject series in
colour and the context in recessive grey, direct labels only where they carry
meaning, and no gradients or 3-D.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
VIOLET = "#4a3aa7"
GREY = "#8f9aa6"
DARK_GREY = "#4f5a64"

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


def _finish(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path


def intraday_shape(index_by_year: dict[int, dict[int, float]], path: Path) -> Path:
    """Hour-of-day price indexed to each year's own baseload (=100)."""
    years = sorted(index_by_year)
    first, last = years[0], years[-1]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))

    for year in years:
        if year in (first, last):
            continue
        values = [index_by_year[year][h] for h in range(24)]
        ax.plot(range(24), values, color=GREY, linewidth=1.4, zorder=1)

    ax.axhline(100, color=DARK_GREY, linewidth=1.2, linestyle="--", zorder=2)
    ax.plot(range(24), [index_by_year[first][h] for h in range(24)],
            color=ORANGE, linewidth=2.6, zorder=3)
    ax.plot(range(24), [index_by_year[last][h] for h in range(24)],
            color=BLUE, linewidth=2.8, zorder=4)

    ax.set_xlabel("Hour of day (Czech local time)")
    ax.set_ylabel("Price, indexed to that year's baseload = 100")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=11)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", labelsize=11)

    ax.annotate(str(first), (13, index_by_year[first][13]),
                textcoords="offset points", xytext=(6, 10),
                fontsize=11.5, fontweight="bold", color=ORANGE)
    ax.annotate(str(last), (13, index_by_year[last][13]),
                textcoords="offset points", xytext=(6, -16),
                fontsize=11.5, fontweight="bold", color=BLUE)
    # The reference line needs naming, and at larger type there is nowhere inside
    # the plot that does not collide with a year line. So the label goes outside
    # the data area, in a margin opened up for it.
    ax.annotate("baseload =\nthe market\naverage", (23.6, 100),
                ha="left", va="center", fontsize=10.5, color=DARK_GREY,
                annotation_clip=False)
    ax.set_xlim(-0.3, 23.4)
    fig.subplots_adjust(right=0.86)
    return _finish(fig, path)


def profile_factors(factors: dict[str, dict[int, float]], names: dict[str, str],
                    path: Path, highlight: tuple[str, ...] = ("office", "night_heavy")) -> Path:
    years = sorted(next(iter(factors.values())))
    fig, ax = plt.subplots(figsize=(8.6, 4.8))

    colours = {highlight[0]: BLUE, highlight[1]: ORANGE}
    for key, series in factors.items():
        values = [series[y] for y in years]
        if key in highlight:
            ax.plot(years, values, color=colours[key], linewidth=2.8,
                    marker="o", markersize=6, markeredgecolor=SURFACE,
                    markeredgewidth=1.5, zorder=4, label=names[key])
        else:
            ax.plot(years, values, color=GREY, linewidth=1.4, zorder=1)

    ax.axhline(1.0, color=DARK_GREY, linewidth=1.2, linestyle="--", zorder=2)
    ax.set_ylabel("Profile factor (baseload = 1.00)")
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", labelsize=11)

    for key in highlight:
        ax.annotate(f"{factors[key][years[-1]]:.2f}",
                    (years[-1], factors[key][years[-1]]),
                    textcoords="offset points", xytext=(8, 0), va="center",
                    fontsize=11, fontweight="bold", color=colours[key])
    ax.annotate("pays the market average", (years[0], 1.0),
                textcoords="offset points", xytext=(4, 6),
                fontsize=10.5, color=DARK_GREY)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              frameon=False, fontsize=11)
    ax.set_xlim(years[0] - 0.15, years[-1] + 0.45)
    return _finish(fig, path)


def daily_spread(volatility: dict[int, dict], path: Path) -> Path:
    years = sorted(volatility)
    values = [volatility[y]["mean_daily_spread"] for y in years]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    colours = [BLUE if y == years[-1] else GREY for y in years]
    bars = ax.bar([str(y) for y in years], values, color=colours, width=0.6)

    ax.set_ylabel("Average highest-minus-lowest price within a day (EUR/MWh)")
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(labelsize=11)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                f"{value:.0f}", ha="center", fontsize=11, color=INK)
    ax.set_ylim(0, max(values) * 1.15)
    return _finish(fig, path)


def negative_by_hour(hours_by_hour: dict[int, float], year: int,
                     total_hours: float, path: Path) -> Path:
    values = [hours_by_hour.get(h, 0.0) for h in range(24)]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    peak = max(values) if values else 1
    colours = [BLUE if v > peak * 0.25 else GREY for v in values]
    ax.bar(range(24), values, color=colours, width=0.72)

    ax.set_xlabel("Hour of day (Czech local time)")
    ax.set_ylabel(f"Hours with a negative price in {year}")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=11)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", labelsize=11)

    busiest = max(range(24), key=lambda h: values[h])
    ax.annotate(f"{total_hours:.0f} hours in total,\nconcentrated around midday",
                (busiest, values[busiest]), textcoords="offset points",
                xytext=(10, -6), fontsize=11, color=INK)
    return _finish(fig, path)
