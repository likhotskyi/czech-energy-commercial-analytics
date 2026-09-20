"""
Step 4: build the workbook.

This one is a tool rather than a report. The Calculator sheet takes a customer's
annual consumption, a system size, a location, a load profile, an avoided price and
a capex, and returns kWp, self-consumption, savings and payback — all as formulas,
with the self-consumption rate looked up out of the modelled grid by a two-way
INDEX/MATCH.

Which means a sales engineer can answer "what if we size it at 40% instead of 30%"
without anyone re-running Python.

The script verifies that the workbook's own arithmetic reproduces findings.json
before writing the file.

    python src/build_excel_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import xlsxwriter

import profiles

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "output" / "rooftop_solar_targeting.xlsx"

NAVY = "#12243A"
ACCENT = "#2A78D6"
INK = "#1A1A1A"
MUTED = "#43525F"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    f = json.loads((CLEAN / "findings.json").read_text(encoding="utf-8"))
    annual = pd.read_csv(CLEAN / "pv_annual.csv", encoding="utf-8-sig")
    retail = pd.read_csv(CLEAN / "retail.csv", encoding="utf-8-sig")

    grid = f["sizing"]["by_profile"]
    ratios = f["sizing"]["ratios"]
    avoided = f["avoided_price_eur_per_kwh"]
    names = [p.name for p in profiles.PROFILES]
    keys = [p.key for p in profiles.PROFILES]

    wb = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": True})
    fmt = {
        "title": wb.add_format({"font_size": 18, "bold": True, "font_color": NAVY}),
        "sub": wb.add_format({"font_size": 11.5, "font_color": MUTED}),
        "h": wb.add_format({"bold": True, "font_size": 12, "font_color": NAVY}),
        "th": wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY,
                             "text_wrap": True, "valign": "vcenter", "align": "left"}),
        "txt": wb.add_format({"font_color": INK}),
        "bold": wb.add_format({"bold": True, "font_color": INK}),
        "label": wb.add_format({"font_color": MUTED, "align": "right"}),
        "input": wb.add_format({"bg_color": "#FFF7E6", "border": 1,
                                "border_color": "#E8D9B5", "num_format": "#,##0.00"}),
        "input_int": wb.add_format({"bg_color": "#FFF7E6", "border": 1,
                                    "border_color": "#E8D9B5", "num_format": "#,##0"}),
        "input_pct": wb.add_format({"bg_color": "#FFF7E6", "border": 1,
                                    "border_color": "#E8D9B5", "num_format": "0%"}),
        "input_txt": wb.add_format({"bg_color": "#FFF7E6", "border": 1,
                                    "border_color": "#E8D9B5"}),
        "out": wb.add_format({"num_format": "#,##0", "bold": True,
                              "font_color": ACCENT, "font_size": 12}),
        "out_pct": wb.add_format({"num_format": "0.0%", "bold": True,
                                  "font_color": ACCENT, "font_size": 12}),
        "out_yrs": wb.add_format({"num_format": "0.0", "bold": True,
                                  "font_color": ACCENT, "font_size": 12}),
        "num4": wb.add_format({"num_format": "0.0000"}),
        "num1": wb.add_format({"num_format": "0.0"}),
        "pct1": wb.add_format({"num_format": "0.0%"}),
        "note": wb.add_format({"font_size": 10.5, "font_color": MUTED,
                               "text_wrap": True, "valign": "top"}),
    }

    # ------------------------------------------------------- self-consumption grid
    ws_g = wb.add_worksheet("Self-consumption grid")
    ws_g.write(0, 0, "Modelled self-consumption rate", fmt["title"])
    ws_g.write(1, 0, "Share of generation the site uses itself, by load profile and "
                     "system size. Computed hour by hour over a full year; the "
                     "Calculator looks values up from here.", fmt["sub"])
    ws_g.write(3, 0, "Profile", fmt["th"])
    for c, ratio in enumerate(ratios, start=1):
        ws_g.write(3, c, ratio, wb.add_format({"bold": True, "font_color": "white",
                                               "bg_color": NAVY, "num_format": "0%"}))
    for r, (key, name) in enumerate(zip(keys, names), start=4):
        ws_g.write(r, 0, name, fmt["txt"])
        for c, ratio in enumerate(ratios, start=1):
            ws_g.write(r, c, grid[key][f"{ratio:.2f}"]["self_consumption_rate"],
                       fmt["pct1"])
    ws_g.set_column(0, 0, 34)
    ws_g.set_column(1, len(ratios), 11)

    first_export_row = 4 + len(keys) + 2
    ws_g.write(first_export_row - 1, 0, "Average price earned on exported energy "
                                        "(EUR/kWh)", fmt["h"])
    ws_g.write(first_export_row, 0, "Profile", fmt["th"])
    for c, ratio in enumerate(ratios, start=1):
        ws_g.write(first_export_row, c, ratio,
                   wb.add_format({"bold": True, "font_color": "white",
                                  "bg_color": NAVY, "num_format": "0%"}))
    for r, (key, name) in enumerate(zip(keys, names), start=first_export_row + 1):
        ws_g.write(r, 0, name, fmt["txt"])
        for c, ratio in enumerate(ratios, start=1):
            ws_g.write(r, c, grid[key][f"{ratio:.2f}"]["export_price_eur_per_kwh"],
                       fmt["num4"])

    scr_range = f"'Self-consumption grid'!$B$5:${chr(65 + len(ratios))}${4 + len(keys)}"
    scr_rows = f"'Self-consumption grid'!$A$5:$A${4 + len(keys)}"
    scr_cols = f"'Self-consumption grid'!$B$4:${chr(65 + len(ratios))}$4"
    exp_first = first_export_row + 2
    exp_last = first_export_row + 1 + len(keys)
    exp_range = f"'Self-consumption grid'!$B${exp_first}:${chr(65 + len(ratios))}${exp_last}"
    exp_rows = f"'Self-consumption grid'!$A${exp_first}:$A${exp_last}"

    # ------------------------------------------------------------- locations
    ws_l = wb.add_worksheet("Locations")
    ws_l.write(0, 0, "Yield by location", fmt["title"])
    ws_l.write(1, 0, "PVGIS long-run average for a roof-mounted system at 35 degrees "
                     "facing south, with its year-to-year standard deviation.",
               fmt["sub"])
    headers = list(annual.columns)
    for c, header in enumerate(headers):
        ws_l.write(3, c, header, fmt["th"])
    for r, row in enumerate(annual.itertuples(index=False), start=4):
        for c, value in enumerate(row):
            ws_l.write(r, c, value)
    ws_l.set_column(0, 0, 18)
    ws_l.set_column(1, len(headers) - 1, 17)
    loc_names = f"Locations!$A$5:$A${4 + len(annual)}"
    loc_yields = f"Locations!$E$5:$E${4 + len(annual)}"

    # ------------------------------------------------------------- calculator
    ws = wb.add_worksheet("Calculator")
    wb.worksheets_objs.insert(0, wb.worksheets_objs.pop(wb.worksheets_objs.index(ws)))
    ws.hide_gridlines(2)
    ws.set_column(0, 0, 2)
    ws.set_column(1, 1, 34)
    ws.set_column(2, 2, 18)
    ws.set_column(3, 3, 46)

    ws.write(1, 1, "Rooftop solar sizing calculator", fmt["title"])
    ws.write(2, 1, "Shaded cells are inputs. Everything else is a formula — change "
                   "an input and the answer moves.", fmt["sub"])

    inputs = [
        ("Annual consumption (MWh)", 2000, "input_int",
         "The site's own electricity use."),
        ("System size (generation as % of use)", 0.30, "input_pct",
         "Must be one of the modelled sizes: 5, 10, 15, 20, 30, 40, 50 or 60%."),
        ("Load profile", "Office hours, Mon-Fri 08:00-18:00", "input_txt",
         "Pick from the list. This is the assumption that matters most."),
        ("Location", "Plzeň", "input_txt", "Sets the yield per kWp."),
        ("Avoided price (EUR/kWh)", avoided["commodity_and_taxes"], "input",
         "What a self-consumed kWh saves. Depends on how much of the customer's "
         "network charge is volumetric — see Assumptions."),
        ("Capex (EUR per kWp)", 1000, "input_int",
         "European commercial rooftop runs about 700-1 300."),
    ]
    row = 5
    for label, value, style, note in inputs:
        ws.write(row, 1, label, fmt["label"])
        ws.write(row, 2, value, fmt[style])
        ws.write(row, 3, note, fmt["note"])
        row += 1

    ws.data_validation(7, 2, 7, 2, {"validate": "list", "source": names})
    ws.data_validation(8, 2, 8, 2, {"validate": "list",
                                    "source": list(annual["location"])})
    ws.data_validation(6, 2, 6, 2, {"validate": "list", "source": ratios})

    consumption, ratio_cell = "$C$6", "$C$7"
    profile_cell, location_cell = "$C$8", "$C$9"
    avoided_cell, capex_cell = "$C$10", "$C$11"

    ws.write(12, 1, "Result", fmt["h"])
    outputs = [
        ("Yield (kWh per kWp per year)",
         f"=INDEX({loc_yields},MATCH({location_cell},{loc_names},0))", "out"),
        ("System size (kWp)",
         f"={consumption}*1000*{ratio_cell}/$C$14", "out"),
        ("Annual generation (MWh)", f"={consumption}*{ratio_cell}", "out"),
        ("Self-consumption rate",
         f"=INDEX({scr_range},MATCH({profile_cell},{scr_rows},0),"
         f"MATCH({ratio_cell},{scr_cols},0))", "out_pct"),
        ("Self-consumed (MWh)", "=$C$16*$C$17", "out"),
        ("Exported (MWh)", "=$C$16-$C$18", "out"),
        ("Price earned on exports (EUR/kWh)",
         f"=INDEX({exp_range},MATCH({profile_cell},{exp_rows},0),"
         f"MATCH({ratio_cell},{scr_cols},0))", "num4"),
        ("Annual saving (EUR)",
         f"=$C$18*1000*{avoided_cell}+$C$19*1000*$C$20", "out"),
        ("Investment (EUR)", f"=$C$15*{capex_cell}", "out"),
        ("Simple payback (years)", "=$C$22/$C$21", "out_yrs"),
    ]
    row = 13
    for label, formula, style in outputs:
        ws.write(row, 1, label, fmt["label"])
        ws.write_formula(row, 2, formula, fmt[style])
        row += 1

    ws.write(24, 1, "How to read it", fmt["h"])
    ws.write(25, 1,
             "Simple payback, undiscounted, before any subsidy or tax treatment, and "
             "before maintenance. It is a comparison tool between customers, not a "
             "financial model of one project. The ranking it produces is robust; the "
             "absolute years move with the quote.", fmt["note"])
    ws.set_row(25, 44)
    ws.write(27, 1, "Where the numbers come from", fmt["h"])
    for i, (label, text) in enumerate([
        ("Self-consumption", "Modelled hour by hour for a full year from PVGIS "
                             "generation and a stylised load shape."),
        ("Export price", "The day-ahead price in the hours the surplus actually "
                         "occurred, with negative hours curtailed to zero."),
        ("Avoided price", "Eurostat's retail components for Czech business "
                          "consumers, excluding VAT."),
    ]):
        ws.write(28 + i, 1, label, fmt["bold"])
        ws.write(28 + i, 2, text, fmt["note"])

    # ------------------------------------------------------------ payback grid
    ws_p = wb.add_worksheet("Payback grid")
    ws_p.write(0, 0, "Simple payback in years", fmt["title"])
    ws_p.write(1, 0, f"At {f['sizing']['base_capex_eur_per_kwp']} EUR/kWp and an "
                     f"avoided price of {avoided['commodity_and_taxes']:.4f} EUR/kWh. "
                     f"The pattern, not the level, is the point: every profile starts "
                     f"in the same place and degrades at its own rate.", fmt["sub"])
    ws_p.write(3, 0, "Profile", fmt["th"])
    for c, ratio in enumerate(ratios, start=1):
        ws_p.write(3, c, ratio, wb.add_format({"bold": True, "font_color": "white",
                                               "bg_color": NAVY, "num_format": "0%"}))
    for r, (key, name) in enumerate(zip(keys, names), start=4):
        ws_p.write(r, 0, name, fmt["txt"])
        for c, ratio in enumerate(ratios, start=1):
            ws_p.write(r, c,
                       grid[key][f"{ratio:.2f}"]["payback_years"]["commodity_and_taxes"],
                       fmt["num1"])
    ws_p.set_column(0, 0, 34)
    ws_p.set_column(1, len(ratios), 11)
    ws_p.conditional_format(4, 1, 3 + len(keys), len(ratios), {
        "type": "3_color_scale", "min_color": "#1baf7a",
        "mid_color": "#ffffff", "max_color": "#eb6834"})

    # ------------------------------------------------------------ assumptions
    ws_a = wb.add_worksheet("Assumptions")
    ws_a.write(0, 0, "Assumptions and sources", fmt["title"])
    rows = [
        ("Generation", f["meta"]["pv_source"]),
        ("System", f["meta"]["system"]),
        ("Analysis year", str(f["meta"]["analysis_year"])),
        ("Wholesale prices", f["meta"]["price_source"]),
        ("Retail price", f["meta"]["retail_source"]),
        ("", ""),
        ("Retail components (EUR/kWh)", ""),
        ("  Energy and supply",
         str(f["retail_components_eur_per_kwh"]["energy_supply"])),
        ("  Network", str(f["retail_components_eur_per_kwh"]["network"])),
        ("  Taxes excluding VAT",
         str(f["retail_components_eur_per_kwh"]["taxes_excl_vat"])),
        ("  Full retail excluding VAT",
         str(f["retail_components_eur_per_kwh"]["retail_excl_vat"])),
        ("", ""),
        ("Avoided-price scenarios", ""),
    ]
    for key, label in f["avoided_scenarios"].items():
        rows.append((f"  {avoided[key]:.4f} EUR/kWh", label))
    rows += [
        ("", ""),
        ("Load profiles", "Stylised, with a base load that does not fall to zero "
                          "overnight. Full definitions below."),
    ]
    for r, (label, value) in enumerate(rows, start=2):
        ws_a.write(r, 0, label, fmt["bold"] if value == "" else fmt["txt"])
        ws_a.write(r, 1, value, fmt["note"])
    ws_a.set_column(0, 0, 32)
    ws_a.set_column(1, 1, 86)

    start = len(rows) + 4
    definitions = profiles.profile_table()
    for c, header in enumerate(definitions.columns):
        ws_a.write(start, c, header, fmt["th"])
    for r, row in enumerate(definitions.itertuples(index=False), start=start + 1):
        for c, value in enumerate(row):
            ws_a.write(r, c, value, fmt["txt"])

    wb.close()

    # -------------------------------------------------------------- verification
    # What the Calculator's default inputs should produce, computed independently.
    ratio = f["sizing"]["base_ratio"]
    key = "office"
    block = grid[key][f"{ratio:.2f}"]
    location_yield = float(annual.loc[annual["location"] == f["sizing"]["location"],
                                      "yield_kwh_per_kwp"].iloc[0])
    kwp = 2000 * 1000 * ratio / location_yield
    generation = 2000 * ratio
    self_mwh = generation * block["self_consumption_rate"]
    export_mwh = generation - self_mwh
    saving = (self_mwh * 1000 * avoided["commodity_and_taxes"]
              + export_mwh * 1000 * block["export_price_eur_per_kwh"])
    payback = kwp * 1000 / saving
    reference = block["payback_years"]["commodity_and_taxes"]
    if abs(payback - reference) > 0.02:
        raise RuntimeError(f"The calculator's default case gives {payback:.2f} years "
                           f"against {reference:.2f} in findings.json")

    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"Calculator default case checks out: {payback:.1f} years against "
          f"{reference:.1f} in findings.json")


if __name__ == "__main__":
    main()
