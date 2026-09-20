"""
Step 6 (optional): reshape the cleaned data into a star schema for Power BI.

The analysis tables are shaped for pandas: wide, denormalised, one file per
question. A BI model wants the opposite — narrow fact tables surrounded by small
dimension tables, joined on keys. Loading the analysis CSVs straight into Power BI
gives one flat table and a report that cannot slice properly.

So this script builds:

    fact_prices        one row per country x band x period x commodity
    fact_components    one row per country x year, components still in columns
                       (deliberately: they are unpivoted in Power Query, which is
                       where a reviewer can see the transformation)

    dim_country        with a role column, so "EU average" can be excluded from
                       rankings without hard-coding a name in every measure
    dim_band           with an explicit sort order, because bands sort
                       alphabetically otherwise and the size curve becomes noise
    dim_period         with a numeric sort key for the half-yearly periods
    dim_component      with the column that carries the whole business point:
                       who sets that part of the price

    python src/build_powerbi_model.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "powerbi"

HOME = "Czechia"
REFERENCE = "EU average"
FOCUS_BAND = "MWH2000-19999"

# Order matters and cannot be inferred from the label: "20-499 MWh" sorts before
# "2 000-19 999 MWh" alphabetically, which is wrong by a factor of a hundred.
ELECTRICITY_BAND_ORDER = [
    "MWH_LT20", "MWH20-499", "MWH500-1999", "MWH2000-19999",
    "MWH20000-69999", "MWH70000-149999", "MWH_GE150000",
]
GAS_BAND_ORDER = [
    "GJ_LT1000", "GJ1000-9999", "GJ10000-99999", "GJ100000-999999", "GJ_GE1000000",
]

COMPONENTS = [
    ("energy_supply", "Energy & supply", 1, "Supplier",
     "The commodity. The only part a supplier sets, and the only part open to "
     "competition."),
    ("network_costs", "Network charges", 2, "Regulator",
     "Delivery over the wires. Set by the Energy Regulatory Office; identical "
     "whichever supplier the customer signs with."),
    ("taxes_excl_vat", "Taxes and levies", 3, "State",
     "Electricity tax and the renewable support levy. Set by law."),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    electricity = pd.read_csv(CLEAN / "electricity_prices.csv", encoding="utf-8-sig")
    gas = pd.read_csv(CLEAN / "gas_prices.csv", encoding="utf-8-sig")
    components = pd.read_csv(CLEAN / "price_components.csv", encoding="utf-8-sig")

    # ------------------------------------------------------------ fact_prices
    electricity = electricity.assign(commodity="Electricity")
    gas = gas.assign(commodity="Gas")
    prices = pd.concat([electricity, gas], ignore_index=True)

    fact_prices = prices.rename(columns={
        "nrg_cons": "band_code",
        "price_eur_per_unit": "price_eur_kwh",
    })[["geo", "band_code", "period", "commodity", "price_eur_kwh"]]

    # A composite key would be tidier still, but Power BI joins happily on three
    # single-column relationships and they are easier to read in the model view.
    fact_prices.to_csv(OUT / "fact_prices.csv", index=False, encoding="utf-8-sig")

    # -------------------------------------------------------- fact_components
    # Left wide on purpose: unpivoting is done in Power Query so the step is
    # visible in the query editor rather than buried in Python.
    fact_components = components[["geo", "year", "energy_supply", "network_costs",
                                  "taxes_excl_vat", "total_excl_vat"]]
    fact_components.to_csv(OUT / "fact_components.csv", index=False,
                           encoding="utf-8-sig")

    # ------------------------------------------------------------ dim_country
    countries = (prices[["geo", "country"]].drop_duplicates()
                 .sort_values("country").reset_index(drop=True))
    countries["role"] = "Peer"
    countries.loc[countries["country"] == HOME, "role"] = "Home"
    countries.loc[countries["country"] == REFERENCE, "role"] = "Reference"
    # A plain Yes/No column so a measure can write dim_country[is_reference]="No"
    # instead of naming the EU row, which would break when the label changes.
    countries["is_reference"] = (countries["role"] == "Reference").map(
        {True: "Yes", False: "No"})
    countries["country_order"] = range(1, len(countries) + 1)
    countries.to_csv(OUT / "dim_country.csv", index=False, encoding="utf-8-sig")

    # --------------------------------------------------------------- dim_band
    band_rows = []
    for order, code in enumerate(ELECTRICITY_BAND_ORDER, start=1):
        band_rows.append({"band_code": code, "commodity": "Electricity",
                          "band_order": order})
    for order, code in enumerate(GAS_BAND_ORDER, start=1):
        band_rows.append({"band_code": code, "commodity": "Gas",
                          "band_order": 100 + order})
    bands = pd.DataFrame(band_rows)

    labels = prices[["nrg_cons", "band"]].drop_duplicates().rename(
        columns={"nrg_cons": "band_code", "band": "band_name"})
    bands = bands.merge(labels, on="band_code", how="left")
    bands["is_focus"] = (bands["band_code"] == FOCUS_BAND).map(
        {True: "Yes", False: "No"})

    # A band with no observations anywhere has no label either, because the label
    # comes from the data. Keeping it would add an empty category to every visual,
    # so it is dropped here and reported rather than silently carried.
    unused = bands[bands["band_name"].isna()]["band_code"].tolist()
    bands = bands[bands["band_name"].notna()].copy()
    bands.sort_values("band_order").to_csv(OUT / "dim_band.csv", index=False,
                                           encoding="utf-8-sig")

    # ------------------------------------------------------------- dim_period
    periods = prices[["period", "year", "semester", "period_start"]].drop_duplicates()
    periods = periods.sort_values("period").reset_index(drop=True)
    periods["period_sort"] = periods["year"] * 10 + periods["semester"]
    periods["half"] = "H" + periods["semester"].astype(str)
    periods.to_csv(OUT / "dim_period.csv", index=False, encoding="utf-8-sig")

    # --------------------------------------------------------------- dim_year
    # The two fact tables sit at different grains: prices are half-yearly,
    # components annual. Forcing both onto one date table would need a
    # many-to-many relationship and would let a user filter to "2025-S1" and see
    # a full-year component figure without any warning. Two separate dimensions,
    # two separate pages, no ambiguity.
    years = pd.DataFrame({"year": sorted(components["year"].unique())})
    years.to_csv(OUT / "dim_year.csv", index=False, encoding="utf-8-sig")

    # ---------------------------------------------------------- dim_component
    pd.DataFrame(COMPONENTS, columns=["component_code", "component_name",
                                      "component_order", "set_by", "note"]
                 ).to_csv(OUT / "dim_component.csv", index=False,
                          encoding="utf-8-sig")

    # ------------------------------------------------------------------ check
    # Every key in the facts must exist in its dimension, or Power BI silently
    # files those rows under a blank row and the totals stop adding up.
    problems = []
    for key, dim, column in [("geo", countries, "geo"),
                             ("band_code", bands, "band_code"),
                             ("period", periods, "period")]:
        orphans = set(fact_prices[key]) - set(dim[column])
        if orphans:
            problems.append(f"{key}: {sorted(orphans)[:5]}")
    orphan_geo = set(fact_components["geo"]) - set(countries["geo"])
    if orphan_geo:
        problems.append(f"components geo: {sorted(orphan_geo)}")
    orphan_year = set(fact_components["year"]) - set(years["year"])
    if orphan_year:
        problems.append(f"components year: {sorted(orphan_year)}")
    if problems:
        raise RuntimeError("Fact rows with no matching dimension row:\n  "
                           + "\n  ".join(problems))

    print(f"fact_prices       {len(fact_prices):>6,} rows")
    print(f"fact_components   {len(fact_components):>6,} rows")
    print(f"dim_country       {len(countries):>6,} rows")
    print(f"dim_band          {len(bands):>6,} rows")
    print(f"dim_period        {len(periods):>6,} rows")
    print(f"dim_year          {len(years):>6,} rows")
    print(f"dim_component     {len(COMPONENTS):>6,} rows")
    if unused:
        print(f"\nDropped {len(unused)} band(s) with no observations in the data: "
              f"{', '.join(unused)}")
        print("Eurostat does not publish them for these countries.")
    print("\nEvery fact key matches a dimension row.")
    print(f"Written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
