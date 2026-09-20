"""
Step 2: turn the cached Eurostat responses into tidy, analysis-ready tables --
and check them before anything is built on top.

    python src/build_dataset.py

The important work here is the reconciliation. Eurostat publishes business
electricity prices twice: as a headline series (nrg_pc_205, half-yearly) and as a
breakdown into components (nrg_pc_205_c, annual). The two must agree, and naively
adding the components up shows they do not -- the sum overshoots the headline
price by about 20%.

The reason is that `TAX_FEE_LEV_CHRG` ("taxes, fees, levies and charges") is a
total that already contains VAT, which the headline series excludes. Subtract VAT
and the two sources agree to a median of 0.7%. Anyone who skips this check
publishes an industrial price roughly a fifth too high.

Outputs
    data/clean/electricity_prices.csv   headline price, all bands, 2007-
    data/clean/gas_prices.csv           the same for gas
    data/clean/price_components.csv     reconciled components, band ID
    data/clean/reconciliation.csv       the check itself, kept as evidence
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import eurostat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

FOCUS_BAND = "MWH2000-19999"

# Short, readable names for the consumption bands. Eurostat's own codes are
# unreadable in a chart legend and the labels are too long for an axis.
BAND_NAMES = {
    "MWH_LT20": "< 20 MWh",
    "MWH20-499": "20-499 MWh",
    "MWH500-1999": "500-1 999 MWh",
    "MWH2000-19999": "2 000-19 999 MWh",
    "MWH20000-69999": "20 000-69 999 MWh",
    "MWH70000-149999": "70 000-149 999 MWh",
    "MWH_GE150000": ">= 150 000 MWh",
}
BAND_ORDER = list(BAND_NAMES)

GAS_BAND_NAMES = {
    "GJ_LT1000": "< 1 000 GJ",
    "GJ1000-9999": "1 000-9 999 GJ",
    "GJ10000-99999": "10 000-99 999 GJ",
    "GJ100000-999999": "100 000-999 999 GJ",
    "GJ_GE1000000": ">= 1 000 000 GJ",
}

COUNTRY_NAMES = {
    "EU27_2020": "EU average", "CZ": "Czechia", "DE": "Germany",
    "AT": "Austria", "PL": "Poland", "SK": "Slovakia", "HU": "Hungary",
}


def load(dataset: str) -> pd.DataFrame:
    payload = json.loads((RAW / f"{dataset}.json").read_text(encoding="utf-8"))
    frame = eurostat.to_frame(payload)
    frame.attrs["updated"] = payload.get("updated", "")
    frame.attrs["dataset_label"] = payload.get("label", "")
    return frame


def tidy_prices(frame: pd.DataFrame, band_names: dict[str, str]) -> pd.DataFrame:
    out = frame.rename(columns={"value": "price_eur_per_unit"}).copy()

    # Belt and braces: even with the unit pinned in the query, assert that one
    # country/band/period yields exactly one price. Silent duplication is the
    # failure mode that survives review, because the averages still look sane.
    if "unit" in out.columns and out["unit"].nunique() > 1:
        out = out[out["unit"] == "KWH"]
    duplicated = out.duplicated(subset=["geo", "nrg_cons", "time"]).sum()
    if duplicated:
        raise RuntimeError(f"{duplicated} duplicate observations: the query is not "
                           f"pinned to a single unit / tax basis / currency.")

    out["country"] = out["geo"].map(COUNTRY_NAMES).fillna(out["geo"])
    out["band"] = out["nrg_cons"].map(band_names).fillna(out["nrg_cons"])
    out["period"] = out["time"]
    out["period_start"] = out["time"].map(eurostat.semester_to_date)
    out["year"] = out["period_start"].dt.year
    out["semester"] = out["time"].str[-1].astype(int)
    return out[["geo", "country", "nrg_cons", "band", "period", "period_start",
                "year", "semester", "price_eur_per_unit"]].sort_values(
                    ["country", "band", "period_start"])


def build_components() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconcile the component breakdown against the headline price series."""
    components = load("nrg_pc_205_c")
    wide = components.pivot_table(index=["geo", "time"], columns="nrg_prc",
                                  values="value").reset_index()

    required = ["NRG_SUP", "NETC", "TAX_FEE_LEV_CHRG", "VAT"]
    missing = [c for c in required if c not in wide.columns]
    if missing:
        raise RuntimeError(f"Eurostat changed the component codes; missing {missing}")

    # The correction this whole module exists for.
    wide["taxes_excl_vat"] = wide["TAX_FEE_LEV_CHRG"] - wide["VAT"]
    wide["total_excl_vat"] = wide["NRG_SUP"] + wide["NETC"] + wide["taxes_excl_vat"]

    # Headline series, averaged over the two semesters, as the reference.
    headline = load("nrg_pc_205")
    headline = headline[headline["nrg_cons"] == FOCUS_BAND].copy()
    headline["year"] = headline["time"].str[:4]
    annual = (headline.groupby(["geo", "year"])["value"].mean()
                      .rename("headline_excl_vat").reset_index())

    check = wide.merge(annual, left_on=["geo", "time"], right_on=["geo", "year"],
                       how="inner")
    check["deviation_pct"] = ((check["total_excl_vat"] / check["headline_excl_vat"] - 1)
                              * 100).round(2)

    # A naive sum (forgetting that the tax total contains VAT) for comparison --
    # this column is what makes the size of the trap visible in the output.
    check["naive_sum"] = check["NRG_SUP"] + check["NETC"] + check["TAX_FEE_LEV_CHRG"]
    check["naive_deviation_pct"] = ((check["naive_sum"] / check["headline_excl_vat"] - 1)
                                    * 100).round(2)

    median_deviation = check["deviation_pct"].abs().median()
    if median_deviation > 3:
        raise RuntimeError(
            f"Components no longer reconcile with the headline series "
            f"(median deviation {median_deviation:.1f}%). Do not publish these numbers "
            f"until the cause is understood."
        )

    tidy = check.copy()
    tidy["country"] = tidy["geo"].map(COUNTRY_NAMES).fillna(tidy["geo"])
    tidy["year"] = tidy["time"].astype(int)
    tidy["energy_supply"] = tidy["NRG_SUP"]
    tidy["network_costs"] = tidy["NETC"]
    tidy["share_energy_supply"] = tidy["energy_supply"] / tidy["total_excl_vat"]
    tidy["share_network"] = tidy["network_costs"] / tidy["total_excl_vat"]
    tidy["share_taxes"] = tidy["taxes_excl_vat"] / tidy["total_excl_vat"]

    columns = ["geo", "country", "year", "energy_supply", "network_costs",
               "taxes_excl_vat", "total_excl_vat", "headline_excl_vat",
               "share_energy_supply", "share_network", "share_taxes",
               "deviation_pct"]
    reconciliation = check[["geo", "time", "NRG_SUP", "NETC", "TAX_FEE_LEV_CHRG",
                            "VAT", "naive_sum", "naive_deviation_pct",
                            "total_excl_vat", "headline_excl_vat", "deviation_pct"]]
    return tidy[columns].sort_values(["country", "year"]), reconciliation


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)

    electricity = load("nrg_pc_205")
    updated = electricity.attrs["updated"][:10]
    elec = tidy_prices(electricity, BAND_NAMES)
    elec.to_csv(CLEAN / "electricity_prices.csv", index=False, encoding="utf-8-sig")

    gas = tidy_prices(load("nrg_pc_203"), GAS_BAND_NAMES)
    gas.to_csv(CLEAN / "gas_prices.csv", index=False, encoding="utf-8-sig")

    comp, recon = build_components()
    comp.to_csv(CLEAN / "price_components.csv", index=False, encoding="utf-8-sig")
    recon.to_csv(CLEAN / "reconciliation.csv", index=False, encoding="utf-8-sig")

    (CLEAN / "source.json").write_text(json.dumps({
        "source": "Eurostat",
        "datasets": {
            "nrg_pc_205": "Electricity prices for non-household consumers (half-yearly)",
            "nrg_pc_205_c": "Electricity price components for non-household consumers (annual)",
            "nrg_pc_203": "Gas prices for non-household consumers (half-yearly)",
        },
        "last_updated_by_eurostat": updated,
        "tax_basis": "Excluding VAT and other recoverable taxes",
        "currency": "EUR",
    }, indent=2), encoding="utf-8")

    print(f"electricity_prices.csv  {len(elec):>5,} rows  "
          f"({elec['period'].min()} - {elec['period'].max()})")
    print(f"gas_prices.csv          {len(gas):>5,} rows")
    print(f"price_components.csv    {len(comp):>5,} rows  "
          f"({comp['year'].min()} - {comp['year'].max()})")
    print(f"\nReconciliation against the headline series:")
    print(f"  correct method (tax total minus VAT): median deviation "
          f"{recon['deviation_pct'].abs().median():.1f}%")
    print(f"  naive sum of components:              median deviation "
          f"{recon['naive_deviation_pct'].abs().median():.1f}%")
    print(f"\nEurostat last updated these series on {updated}.")


if __name__ == "__main__":
    main()
