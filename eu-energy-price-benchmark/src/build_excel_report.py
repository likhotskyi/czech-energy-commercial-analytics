"""
Step 4: build the workbook an analyst would actually be handed.

The summary sheets are **live Excel formulas** (SUMIFS / AVERAGEIFS / INDEX-MATCH
over named tables), not values Python pasted in. Someone can filter the data,
add a country, or drop their own PivotTable on top and every number recalculates.
A workbook of hard-coded values is dead the first time anyone edits it.

One detail that is easy to get wrong and hard to notice: boolean TRUE/FALSE
columns are unreliable as SUMIFS criteria and in Power BI slicers, so anything
flag-like is written as text.

    python src/build_excel_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "output" / "czech_industrial_energy_benchmark.xlsx"

NAVY = "#12243A"
ACCENT = "#2A78D6"
INK = "#1A1A1A"
MUTED = "#43525F"
HOME = "Czechia"
REFERENCE = "EU average"
FOCUS_BAND = "2 000-19 999 MWh"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    elec = pd.read_csv(CLEAN / "electricity_prices.csv", encoding="utf-8-sig")
    gas = pd.read_csv(CLEAN / "gas_prices.csv", encoding="utf-8-sig")
    comp = pd.read_csv(CLEAN / "price_components.csv", encoding="utf-8-sig")
    recon = pd.read_csv(CLEAN / "reconciliation.csv", encoding="utf-8-sig")
    findings = json.loads((CLEAN / "findings.json").read_text(encoding="utf-8"))
    meta = findings["meta"]

    wb = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": True})
    f = {
        "title": wb.add_format({"font_size": 18, "bold": True, "font_color": NAVY}),
        "sub": wb.add_format({"font_size": 11.5, "font_color": MUTED}),
        "h": wb.add_format({"bold": True, "font_size": 12, "font_color": NAVY}),
        "th": wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY,
                             "text_wrap": True, "valign": "vcenter", "align": "left"}),
        "txt": wb.add_format({"font_color": INK}),
        "bold": wb.add_format({"bold": True, "font_color": INK}),
        "cents": wb.add_format({"num_format": "0.00"}),
        "eur": wb.add_format({"num_format": "0.0000"}),
        "pct": wb.add_format({"num_format": "0.0%"}),
        "pct1": wb.add_format({"num_format": "+0.0%;-0.0%;0.0%"}),
        "num": wb.add_format({"num_format": "#,##0"}),
        "kpi_label": wb.add_format({"font_size": 10.5, "font_color": MUTED}),
        "kpi": wb.add_format({"font_size": 20, "bold": True, "font_color": ACCENT,
                              "num_format": "0.00"}),
        "kpi_pct": wb.add_format({"font_size": 20, "bold": True, "font_color": ACCENT,
                                  "num_format": "0.0%"}),
        "note": wb.add_format({"font_size": 10.5, "font_color": MUTED,
                               "text_wrap": True, "valign": "top"}),
    }

    # ------------------------------------------------------- data sheets
    def write_table(sheet_name: str, frame: pd.DataFrame, table_name: str,
                    widths: dict[int, int] | None = None):
        ws = wb.add_worksheet(sheet_name)
        ws.freeze_panes(1, 0)
        records = frame.where(pd.notna(frame), None).values.tolist()
        for r, row in enumerate(records, start=1):
            for c, value in enumerate(row):
                if value is not None:
                    ws.write(r, c, value)
        ws.add_table(0, 0, len(records), len(frame.columns) - 1, {
            "name": table_name,
            "columns": [{"header": c, "header_format": f["th"]} for c in frame.columns],
            "style": "Table Style Light 8",
        })
        ws.set_column(0, len(frame.columns) - 1, 16)
        for col, width in (widths or {}).items():
            ws.set_column(col, col, width)
        return ws

    elec_out = elec.drop(columns=["period_start"])
    write_table("Electricity data", elec_out, "Electricity", {1: 14, 3: 20, 4: 12})
    write_table("Gas data", gas.drop(columns=["period_start"]), "Gas", {1: 14, 3: 20})
    write_table("Components", comp, "Components", {1: 14})
    write_table("Reconciliation", recon, "Reconciliation", {1: 12})

    def C(table: str, column: str) -> str:
        return f"{table}[{column}]"

    # ------------------------------------------------- benchmark (formulas)
    ws = wb.add_worksheet("Benchmark")
    ws.write(0, 0, f"Business electricity price, {FOCUS_BAND}", f["title"])
    ws.write(1, 0, "Every figure is a live AVERAGEIFS over the Electricity table — "
                   "edit the data and this recalculates.", f["sub"])

    countries = meta["countries"]
    periods = sorted(elec[elec["band"] == FOCUS_BAND]["period"].unique())
    recent_periods = periods[-8:]

    ws.write(3, 0, "Country", f["th"])
    for c, period in enumerate(recent_periods, start=1):
        ws.write(3, c, period, f["th"])
    ws.write(3, len(recent_periods) + 1, "vs EU average", f["th"])

    for r, country in enumerate(countries, start=4):
        ws.write(r, 0, country, f["bold"] if country == HOME else f["txt"])
        for c, period in enumerate(recent_periods, start=1):
            ws.write_formula(
                r, c,
                f'=IFERROR(AVERAGEIFS({C("Electricity", "price_eur_per_unit")},'
                f'{C("Electricity", "country")},$A{r + 1},'
                f'{C("Electricity", "band")},"{FOCUS_BAND}",'
                f'{C("Electricity", "period")},"{period}")*100,"")',
                f["cents"])
        last_col = xlsxwriter.utility.xl_col_to_name(len(recent_periods))
        eu_row = countries.index(REFERENCE) + 5
        ws.write_formula(
            r, len(recent_periods) + 1,
            f'=IFERROR({last_col}{r + 1}/{last_col}${eu_row}-1,"")', f["pct1"])

    ws.set_column(0, 0, 18)
    ws.set_column(1, len(recent_periods) + 1, 12)
    ws.write(len(countries) + 5, 0,
             "Prices in EUR cents per kWh, excluding VAT. VAT is recoverable for a "
             "business, so the VAT-inclusive series overstates what a company pays.",
             f["note"])

    # --------------------------------------------- composition (formulas)
    ws2 = wb.add_worksheet("Composition")
    latest_year = findings["composition"]["year"]
    ws2.write(0, 0, f"What the bill is made of, {latest_year}", f["title"])
    ws2.write(1, 0, "Energy & supply is the only part a supplier sets. Network charges "
                    "and taxes are identical whichever supplier the customer signs with.",
              f["sub"])
    headers = ["Country", "Energy & supply", "Network costs", "Taxes excl. VAT",
               "Total", "Commodity share", "A 10% commodity cut takes this off the bill"]
    for c, header in enumerate(headers):
        ws2.write(3, c, header, f["th"])

    for r, country in enumerate(countries, start=4):
        ws2.write(r, 0, country, f["bold"] if country == HOME else f["txt"])
        for c, column in enumerate(["energy_supply", "network_costs", "taxes_excl_vat"],
                                   start=1):
            ws2.write_formula(
                r, c,
                f'=IFERROR(SUMIFS({C("Components", column)},'
                f'{C("Components", "country")},$A{r + 1},'
                f'{C("Components", "year")},{latest_year})*100,"")', f["cents"])
        ws2.write_formula(r, 4, f"=SUM(B{r + 1}:D{r + 1})", f["cents"])
        ws2.write_formula(r, 5, f'=IFERROR(B{r + 1}/E{r + 1},"")', f["pct"])
        ws2.write_formula(r, 6, f'=IFERROR(0.1*F{r + 1},"")', f["pct"])

    ws2.set_column(0, 0, 18)
    ws2.set_column(1, 6, 18)
    ws2.set_column(6, 6, 34)
    ws2.conditional_format(4, 5, 3 + len(countries), 5,
                           {"type": "data_bar", "bar_color": ACCENT})

    chart = wb.add_chart({"type": "bar", "subtype": "stacked"})
    for idx, (name, colour) in enumerate([("Energy & supply", "#2a78d6"),
                                          ("Network costs", "#1baf7a"),
                                          ("Taxes excl. VAT", "#eb6834")], start=1):
        chart.add_series({
            "name": name,
            "categories": ["Composition", 4, 0, 3 + len(countries), 0],
            "values": ["Composition", 4, idx, 3 + len(countries), idx],
            "fill": {"color": colour},
        })
    chart.set_title({"name": f"Price components, {latest_year} (EUR cents/kWh)"})
    chart.set_legend({"position": "bottom"})
    chart.set_size({"width": 820, "height": 400})
    ws2.insert_chart(len(countries) + 6, 0, chart)

    # ------------------------------------------------------- band curve
    ws3 = wb.add_worksheet("By consumption band")
    size = findings["size_discount"]
    ws3.write(0, 0, f"Price by consumption band, {size['period']}", f["title"])
    ws3.write(1, 0, size["reason_for_band_choice"], f["sub"])
    bands = list(size["table"].keys())
    ws3.write(3, 0, "Band", f["th"])
    for c, country in enumerate(countries, start=1):
        ws3.write(3, c, country, f["th"])
    for r, band_name in enumerate(bands, start=4):
        ws3.write(r, 0, band_name, f["txt"])
        for c, country in enumerate(countries, start=1):
            ws3.write_formula(
                r, c,
                f'=IFERROR(AVERAGEIFS({C("Electricity", "price_eur_per_unit")},'
                f'{C("Electricity", "country")},{xlsxwriter.utility.xl_col_to_name(c)}$4,'
                f'{C("Electricity", "band")},$A{r + 1},'
                f'{C("Electricity", "period")},"{size["period"]}")*100,"n/a")',
                f["cents"])
    ws3.set_column(0, 0, 22)
    ws3.set_column(1, len(countries), 14)
    ws3.write(len(bands) + 5, 0,
              "'n/a' means the country does not publish that band — usually because too "
              "few consumers fall into it to report without identifying them.", f["note"])

    # ------------------------------------------------------- dashboard
    ws0 = wb.add_worksheet("Summary")
    wb.worksheets_objs.insert(0, wb.worksheets_objs.pop(wb.worksheets_objs.index(ws0)))
    ws0.hide_gridlines(2)
    ws0.set_column(0, 0, 2)
    ws0.set_column(1, 8, 17)
    ws0.write(1, 1, "Czech industrial energy price benchmark", f["title"])
    ws0.write(2, 1, f"Source: Eurostat, updated {meta['last_updated_by_eurostat']}. "
                    f"Band {meta['band']}, {meta['latest_period']}, excluding VAT.", f["sub"])

    price = findings["price_level"]
    composition = findings["composition"]
    lever = findings["discount_leverage"]
    shock = findings["price_shock"]
    kpis = [
        ("CZECH PRICE (EUR cents/kWh)", price["czechia"] * 100, "kpi"),
        ("VS EU AVERAGE", price["gap_vs_eu_pct"] / 100, "kpi_pct"),
        ("VS GERMANY", price["gap_vs_germany_pct"] / 100, "kpi_pct"),
        ("COMMODITY SHARE OF THE BILL", composition["czechia_share_energy_supply_pct"] / 100, "kpi_pct"),
        ("A 10% COMMODITY CUT TAKES OFF", lever["czechia_bill_reduction_pct"] / 100, "kpi_pct"),
        ("STILL ABOVE PRE-CRISIS", shock["vs_pre_crisis_pct"] / 100, "kpi_pct"),
    ]
    for i, (label, value, style) in enumerate(kpis):
        col = 1 + (i % 3) * 2
        row = 4 + (i // 3) * 3
        ws0.write(row, col, label, f["kpi_label"])
        ws0.write(row + 1, col, value, f[style])

    ws0.write(11, 1, "What is in this workbook", f["h"])
    guide = [
        ("Benchmark", "Price by country and semester, as live AVERAGEIFS formulas."),
        ("Composition", "The bill split into energy, network and tax, with the "
                        "leverage a discount actually has."),
        ("By consumption band", "How price falls with size — and where it does not."),
        ("Electricity data / Gas data", "The full tidy series as Excel tables. "
                                        "Insert > PivotTable works on them directly."),
        ("Components", "The reconciled component breakdown."),
        ("Reconciliation", "The check itself: components against the headline series, "
                           "and what the naive method would have produced."),
    ]
    for i, (sheet, what) in enumerate(guide):
        ws0.write(13 + i, 1, sheet, f["bold"])
        ws0.write(13 + i, 2, what, f["note"])

    ws0.write(21, 1, "The one thing to know about this data", f["h"])
    ws0.write(22, 1,
              f"Eurostat's tax total already contains VAT. Adding the components up "
              f"without subtracting it overstates the industrial price by "
              f"{findings['data_quality']['naive_method_median_deviation_pct']:.0f}%. "
              f"Done correctly, the components agree with the published price series to "
              f"{findings['data_quality']['reconciliation_median_deviation_pct']:.1f}%. "
              f"The Reconciliation sheet is the evidence.", f["note"])
    ws0.set_row(22, 46)

    wb.close()
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
