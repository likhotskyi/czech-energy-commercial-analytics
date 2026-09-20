"""
Chart rendering.

Palette slots checked for colour-vision-deficiency separation and contrast against
the surface. One value axis everywhere, a legend only where more than one series
needs naming, the subject in colour and the context in recessive grey, direct
labels only where they carry meaning.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
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


def self_consumption_curve(grid: dict, names: dict[str, str], ratios: list[float],
                           path: Path, highlight: tuple[str, str] = ("office", "night_heavy")) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    colours = {highlight[0]: BLUE, highlight[1]: ORANGE}

    for key, block in grid.items():
        values = [block[f"{r:.2f}"]["self_consumption_rate"] for r in ratios]
        if key in highlight:
            ax.plot(ratios, values, color=colours[key], linewidth=2.8, marker="o",
                    markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5,
                    zorder=4, label=names[key])
        else:
            ax.plot(ratios, values, color=GREY, linewidth=1.5, zorder=1)

    ax.set_xlabel("System size: annual generation as a share of consumption")
    ax.set_ylabel("Share of generation the site consumes itself")
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    ax.set_xticks(ratios)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(labelsize=11)

    for key in highlight:
        final = grid[key][f"{ratios[-1]:.2f}"]["self_consumption_rate"]
        ax.annotate(f"{final:.0%}", (ratios[-1], final), textcoords="offset points",
                    xytext=(9, 0), va="center", fontsize=11, fontweight="bold",
                    color=colours[key])
    # The two end labels carry the comparison; a floating "N points apart" and a
    # note about small systems both landed on top of the grey context lines, and
    # the panel beside the chart already says it in words.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=False, fontsize=11)
    ax.set_xlim(ratios[0] - 0.01, ratios[-1] + 0.06)
    return _finish(fig, path)


def typical_day(series: dict, names: dict[str, str], path: Path,
                profiles_shown: tuple[str, str] = ("office", "night_heavy")) -> Path:
    hours = list(range(24))
    generation = [series["generation_kw"].get(str(h), 0.0) for h in hours]

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.fill_between(hours, generation, color=YELLOW, alpha=0.35, zorder=1,
                    label="Solar generation")
    ax.plot(hours, generation, color=YELLOW, linewidth=2, zorder=2)

    for key, colour in zip(profiles_shown, (BLUE, ORANGE)):
        load = [series[key].get(str(h), 0.0) for h in hours]
        ax.plot(hours, load, color=colour, linewidth=2.6, zorder=3, label=names[key])

    ax.set_xlabel("Hour of an average June weekday (Czech local time)")
    ax.set_ylabel("kW")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=11)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylim(0, max(max(generation),
                       *[max(series[k].values()) for k in profiles_shown]) * 1.18)

    peak_hour = max(hours, key=lambda h: generation[h])
    # Sits low inside the shaded area, clear of both load lines.
    ax.annotate("everything under the lower line is consumed on site",
                (peak_hour, generation[peak_hour] * 0.18),
                ha="center", fontsize=10.5, color=MUTED)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3,
              frameon=False, fontsize=11)
    return _finish(fig, path)


def capture_rate(by_year: dict, path: Path) -> Path:
    years = sorted(int(y) for y in by_year)
    values = [by_year[str(y)]["capture_rate"] for y in years]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    colours = [BLUE if y == years[-1] else GREY for y in years]
    bars = ax.bar([str(y) for y in years], values, color=colours, width=0.6)

    ax.axhline(1.0, color=DARK_GREY, linewidth=1.2, linestyle="--")
    ax.set_ylabel("Price solar earns, against the flat baseload price")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(labelsize=11)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{value:.2f}", ha="center", fontsize=11, color=INK)
    ax.annotate("the baseload price", (len(years) - 0.5, 1.0),
                textcoords="offset points", xytext=(-4, 6), ha="right",
                fontsize=10.5, color=DARK_GREY)
    ax.set_ylim(0, 1.15)
    return _finish(fig, path)


def by_location(results: dict, path: Path) -> Path:
    names = sorted(results, key=lambda k: results[k]["payback_years_at_1000"])
    values = [results[k]["payback_years_at_1000"] for k in names]
    yields = [results[k]["yield_kwh_per_kwp"] for k in names]

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    bars = ax.barh(names, values, color=BLUE, height=0.6)
    ax.invert_yaxis()
    ax.set_xlabel("Simple payback (years) at 1 000 EUR/kWp")
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(labelsize=11.5)

    for bar, value, kwh in zip(bars, values, yields):
        ax.text(bar.get_width() + max(values) * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}    ({kwh:,.0f} kWh/kWp)",
                va="center", fontsize=11, color=INK)
    ax.set_xlim(0, max(values) * 1.32)
    return _finish(fig, path)
