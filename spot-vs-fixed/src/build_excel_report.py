"""
Step 4: build the workbook.

The point of this file is that the profile factors are **computed in Excel**, not
pasted in from Python. The workbook contains:

  * a price grid of year x day type x hour with the hours behind each average, and
  * an editable table of load weights,

and the factors are SUMPRODUCT formulas over the two, with the weights pulled in
by INDEX/MATCH. Change a weight — say, decide that the office base load is 25%
rather than 15% — and every factor recalculates.

This is exact rather than approximate, and it is worth saying why: each profile's
weight depends only on the day type and the hour, so grouping the prices by
(year, day type, hour) and weighting by the hours in each cell reproduces the
settlement-period calculation term for term. The script checks that it does,
against findings.json, and refuses to write a workbook that disagrees.

    python src/build_excel_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xlsxwriter

import profiles

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "output" / "spot_vs_fixed_czech_market.xlsx"

NAVY = "#12243A"
ACCENT = "#2A78D6"
WARM = "#EB6834"
INK = "#1A1A1A"
MUTED = "#43525F"


def build_grid(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, weekend, hour), g in df.groupby(["year", "is_weekend", "hour_local"]):
        hours = float(g["duration_h"].sum())
        rows.append({
            "year": int(year),
            "day_type": "Weekend" if weekend else "Weekday",
            "hour": int(hour),
            "hours_in_period": round(hours, 2),
            "avg_price_eur_mwh": round(
                float(np.average(g["price_eur_mwh"], weights=g["duration_h"])), 4),
            # Single-column join key. The alternative, matching on two columns at
            # once, needs an array formula that older Excel only accepts with
            # Ctrl+Shift+Enter -- a workbook that breaks silently on someone
            # else's machine is worse than one extra column.
            "key": f"{'Weekend' if weekend else 'Weekday'}-{int(hour):02d}",
        })
    return pd.DataFrame(rows).sort_values(["year", "day_type", "hour"])


def build_weights() -> pd.DataFrame:
    rows = []
    for day_type in ("Weekday", "Weekend"):
        for hour in range(24):
            row = {"day_type": day_type, "hour": hour,
                   "key": f"{day_type}-{hour:02d}"}
            hour_series = pd.Series([hour])
            weekend_series = pd.Series([day_type == "Weekend"])
            for profile in profiles.PROFILES:
                row[profile.key] = float(
                    profile.weights(hour_series, weekend_series)[0])
            rows.append(row)
    return pd.DataFrame(rows)


def verify(grid: pd.DataFrame, weights: pd.DataFrame,
           findings: dict) -> list[tuple[str, int, float, float]]:
    """Recompute the factors the way the workbook will, and compare."""
    merged = grid.merge(weights, on=["day_type", "hour"], how="left")
    problems = []
    for profile in profiles.PROFILES:
        for year, g in merged.groupby("year"):
            w = g[profile.key] * g["hours_in_period"]
            factor = float(np.average(g["avg_price_eur_mwh"], weights=w))
            base = float(np.average(g["avg_price_eur_mwh"],
                                    weights=g["hours_in_period"]))
            excel_value = factor / base
            reference = findings["profile_factors"][profile.key][str(year)]
            if abs(excel_value - reference) > 1e-4:
                problems.append((profile.key, int(year), excel_value, reference))
    return problems


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLEAN / "prices.csv", encoding="utf-8-sig")
    findings = json.loads((CLEAN / "findings.json").read_text(encoding="utf-8"))
    coverage = pd.read_csv(CLEAN / "coverage.csv", encoding="utf-8-sig")

    grid = build_grid(df)
    weights = build_weights()

    problems = verify(grid, weights, findings)
    if problems:
        raise RuntimeError(
            "The grid does not reproduce the settlement-period factors: "
            + "; ".join(f"{k} {y}: {a:.4f} vs {b:.4f}" for k, y, a, b in problems[:5]))

    daily = (df.groupby(["date_local", "year", "month", "is_weekend"])
               .apply(lambda g: pd.Series({
                   "baseload_eur_mwh": round(float(np.average(
                       g["price_eur_mwh"], weights=g["duration_h"])), 2),
                   "min_eur_mwh": round(float(g["price_eur_mwh"].min()), 2),
                   "max_eur_mwh": round(float(g["price_eur_mwh"].max()), 2),
                   "negative_hours": round(float(g.loc[g["negative"], "duration_h"].sum()), 2),
               }), include_groups=False)
               .reset_index())
    daily["spread_eur_mwh"] = (daily["max_eur_mwh"] - daily["min_eur_mwh"]).round(2)
    daily["day_type"] = np.where(daily["is_weekend"], "Weekend", "Weekday")
    daily = daily.drop(columns=["is_weekend"])

    years = sorted(grid["year"].unique())

    wb = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": True})
    fmt = {
        "title": wb.add_format({"font_size": 18, "bold": True, "font_color": NAVY}),
        "sub": wb.add_format({"font_size": 11.5, "font_color": MUTED}),
        "h": wb.add_format({"bold": True, "font_size": 12, "font_color": NAVY}),
        "th": wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY,
                             "text_wrap": True, "valign": "vcenter", "align": "left"}),
        "txt": wb.add_format({"font_color": INK}),
        "bold": wb.add_format({"bold": True, "font_color": INK}),
        "num2": wb.add_format({"num_format": "0.00"}),
        "num3": wb.add_format({"num_format": "0.000"}),
        "pct": wb.add_format({"num_format": "+0.0%;-0.0%;0.0%"}),
        "input": wb.add_format({"num_format": "0.00", "bg_color": "#FFF7E6",
                                "border": 1, "border_color": "#E8D9B5"}),
        "kpi_label": wb.add_format({"font_size": 10.5, "font_color": MUTED}),
        "kpi": wb.add_format({"font_size": 20, "bold": True, "font_color": ACCENT,
                              "num_format": "0.00"}),
        "kpi_int": wb.add_format({"font_size": 20, "bold": True, "font_color": ACCENT,
                                  "num_format": "#,##0"}),
        "note": wb.add_format({"font_size": 10.5, "font_color": MUTED,
                               "text_wrap": True, "valign": "top"}),
    }

    def write_table(sheet: str, frame: pd.DataFrame, name: str,
                    widths: dict[int, int] | None = None):
        ws = wb.add_worksheet(sheet)
        ws.freeze_panes(1, 0)
        records = frame.where(pd.notna(frame), None).values.tolist()
        for r, row in enumerate(records, start=1):
            for c, value in enumerate(row):
                if value is not None:
                    ws.write(r, c, value)
        ws.add_table(0, 0, len(records), len(frame.columns) - 1, {
            "name": name,
            "columns": [{"header": c, "header_format": fmt["th"]}
                        for c in frame.columns],
            "style": "Table Style Light 8",
        })
        ws.set_column(0, len(frame.columns) - 1, 17)
        for col, width in (widths or {}).items():
            ws.set_column(col, col, width)
        return ws

    # ---------------------------------------------------------------- inputs
    ws_w = wb.add_worksheet("Load weights")
    ws_w.write(0, 0, "Load weights — edit these", fmt["title"])
    ws_w.write(1, 0, "Relative consumption for each hour and day type. Only the "
                     "shape matters, so scaling a whole column changes nothing. "
                     "The shaded cells are inputs: change one and every factor in "
                     "the workbook recalculates.", fmt["note"])
    ws_w.set_row(1, 30)

    headers = ["day_type", "hour", "key"] + [p.key for p in profiles.PROFILES]
    records = weights[headers].values.tolist()
    for r, row in enumerate(records, start=4):
        for c, value in enumerate(row):
            style = fmt["input"] if c >= 3 else fmt["txt"]
            ws_w.write(r, c, value, style)
    ws_w.add_table(3, 0, 3 + len(records), len(headers) - 1, {
        "name": "Weights",
        "columns": [{"header": h, "header_format": fmt["th"]} for h in headers],
        "style": "Table Style Light 8",
    })
    ws_w.set_column(0, 0, 12)
    ws_w.set_column(1, 1, 8)
    ws_w.set_column(2, 2, 14)
    ws_w.set_column(3, len(headers) - 1, 14)

    # ------------------------------------------------------------- price grid
    # The weight columns must be part of the table, not written beside it: a
    # structured reference such as Grid[w_office] only resolves for a column the
    # table actually declares, and a formula that refers to a column outside it
    # fails with #NAME? in every cell that uses it.
    ws_g = wb.add_worksheet("Price grid")
    ws_g.freeze_panes(1, 0)
    grid_columns = list(grid.columns) + [f"w_{p.key}" for p in profiles.PROFILES]
    first_col = len(grid.columns)

    for r, row in enumerate(grid.values.tolist(), start=1):
        for c, value in enumerate(row):
            ws_g.write(r, c, value)
        for i, profile in enumerate(profiles.PROFILES):
            ws_g.write_formula(
                r, first_col + i,
                f'=INDEX(Weights[{profile.key}],MATCH($F{r + 1},Weights[key],0))',
                fmt["num2"])

    ws_g.add_table(0, 0, len(grid), len(grid_columns) - 1, {
        "name": "Grid",
        "columns": [{"header": c, "header_format": fmt["th"]} for c in grid_columns],
        "style": "Table Style Light 8",
    })
    for col, width in {0: 8, 1: 12, 2: 8, 3: 16, 4: 20, 5: 14}.items():
        ws_g.set_column(col, col, width)
    ws_g.set_column(first_col, len(grid_columns) - 1, 15)

    # --------------------------------------------------------- profile factors
    ws_f = wb.add_worksheet("Profile factors")
    ws_f.write(0, 0, "Profile factor by year", fmt["title"])
    ws_f.write(1, 0, "Baseload = 1.00. Above 1.00 the customer's shape costs it "
                     "money; below 1.00 it saves money. Every cell is a SUMPRODUCT "
                     "over the price grid — nothing here is a pasted value.",
               fmt["sub"])

    ws_f.write(3, 0, "Year", fmt["th"])
    for i, profile in enumerate(profiles.PROFILES):
        ws_f.write(3, 1 + i, profile.name, fmt["th"])
    ws_f.write(3, 1 + len(profiles.PROFILES), "Baseload (EUR/MWh)", fmt["th"])

    for r, year in enumerate(years, start=4):
        ws_f.write(r, 0, year, fmt["bold"])
        cell = f"$A{r + 1}"
        base = (f'SUMPRODUCT((Grid[year]={cell})*Grid[avg_price_eur_mwh]'
                f'*Grid[hours_in_period])/SUMPRODUCT((Grid[year]={cell})'
                f'*Grid[hours_in_period])')
        for i, profile in enumerate(profiles.PROFILES):
            w = f"Grid[w_{profile.key}]"
            ws_f.write_formula(
                r, 1 + i,
                f'=(SUMPRODUCT((Grid[year]={cell})*Grid[avg_price_eur_mwh]*{w}'
                f'*Grid[hours_in_period])/SUMPRODUCT((Grid[year]={cell})*{w}'
                f'*Grid[hours_in_period]))/({base})',
                fmt["num3"])
        ws_f.write_formula(r, 1 + len(profiles.PROFILES), f"={base}", fmt["num2"])

    ws_f.set_column(0, 0, 10)
    ws_f.set_column(1, len(profiles.PROFILES) + 1, 21)
    ws_f.conditional_format(4, 1, 3 + len(years), len(profiles.PROFILES), {
        "type": "3_color_scale",
        "min_color": "#1baf7a", "mid_color": "#ffffff", "max_color": "#eb6834",
    })
    ws_f.write(len(years) + 6, 0, "Assumptions behind each profile", fmt["h"])
    definitions = profiles.profile_table()
    for c, header in enumerate(definitions.columns):
        ws_f.write(len(years) + 7, c, header, fmt["th"])
    for r, row in enumerate(definitions.itertuples(index=False), start=len(years) + 8):
        for c, value in enumerate(row):
            ws_f.write(r, c, value, fmt["txt"])

    # ----------------------------------------------------------------- daily
    write_table("Daily", daily, "Daily", {0: 14})

    # -------------------------------------------------------------- coverage
    write_table("Coverage check", coverage, "Coverage", {0: 8})

    # --------------------------------------------------------------- summary
    ws0 = wb.add_worksheet("Summary")
    wb.worksheets_objs.insert(0, wb.worksheets_objs.pop(wb.worksheets_objs.index(ws0)))
    ws0.hide_gridlines(2)
    ws0.set_column(0, 0, 2)
    ws0.set_column(1, 8, 18)

    meta = findings["meta"]
    inv = findings["inversion"]
    first, last = inv["first_year"], inv["last_year"]
    spread = findings["customer_spread"]["by_year"][str(last)]

    ws0.write(1, 1, "Spot or fixed: what the load shape is worth", fmt["title"])
    ws0.write(2, 1, f"Czech day-ahead market, {first}-{last}. "
                    f"Source: {meta['source']}, {meta['licence']}. "
                    f"{meta['settlement_periods']:,} settlement periods, local time.",
              fmt["sub"])

    kpis = [
        (f"OFFICE PROFILE, {first}", inv["office_first_year"], "kpi"),
        (f"OFFICE PROFILE, {last}", inv["office_latest_year"], "kpi"),
        (f"NIGHT PROFILE, {first}", inv["night_first_year"], "kpi"),
        (f"NIGHT PROFILE, {last}", inv["night_latest_year"], "kpi"),
        (f"SPREAD, EUR/MWh ({last})", spread["spread_eur_per_mwh"], "kpi"),
        (f"EUR/YEAR AT {findings['customer_spread']['example_volume_mwh']:,} MWh",
         spread["spread_eur_per_year_at_example_volume"], "kpi_int"),
    ]
    for i, (label, value, style) in enumerate(kpis):
        col = 1 + (i % 3) * 2
        row = 4 + (i // 3) * 3
        ws0.write(row, col, label, fmt["kpi_label"])
        ws0.write(row + 1, col, value, fmt[style])

    ws0.write(11, 1, "What is in this workbook", fmt["h"])
    guide = [
        ("Profile factors", "The answer, as live SUMPRODUCT formulas over the "
                            "price grid."),
        ("Load weights", "The editable assumptions. Change a base load and the "
                         "factors move."),
        ("Price grid", "Average price by year, day type and hour, with the hours "
                       "behind each average."),
        ("Daily", "One row per day: baseload, high, low, spread, negative hours. "
                  "Built for PivotTables."),
        ("Coverage check", "Hours delivered against the calendar, per year."),
    ]
    for i, (sheet, what) in enumerate(guide):
        ws0.write(13 + i, 1, sheet, fmt["bold"])
        ws0.write(13 + i, 2, what, fmt["note"])

    ws0.write(20, 1, "How to read a profile factor", fmt["h"])
    ws0.write(21, 1,
              "It is the ratio between the average price a customer's own shape "
              "pays and the flat 24/7 average. It isolates the shape effect only: "
              "a real fixed-price offer also carries a forward price, a risk "
              "premium and balancing costs, which are not public data.", fmt["note"])
    ws0.set_row(21, 46)

    wb.close()
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print("Excel factors verified against findings.json "
          f"for {len(profiles.PROFILES)} profiles x {len(years)} years.")


if __name__ == "__main__":
    main()
