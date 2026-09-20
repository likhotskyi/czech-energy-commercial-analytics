"""
Step 3: the model, and every number the workbook, the deck and the report quote.

The economics of rooftop solar on a business site turn on one ratio. A kilowatt-hour
the site consumes itself replaces a kilowatt-hour it would have bought at the retail
price -- energy, network charges and taxes together. A kilowatt-hour it exports earns
only the wholesale price at that moment, and solar generates precisely when wholesale
prices are lowest. The two are worth very different amounts, so **the share of
generation the site consumes itself decides the investment**.

That share is not a property of the roof. It is a property of when the business runs.
Which makes it a sales question: the same system, on the same roof, in the same town,
is a good investment for one customer and a poor one for the next.

Everything here is hourly. For each location, load profile and system size:

    self-consumed = min(generation, load)      hour by hour, never netted annually
    exported      = generation - self-consumed
    savings       = self-consumed x retail price  +  exported x wholesale price

Netting over a month or a year instead would overstate self-consumption enormously,
because it would let August sunshine cancel a February night.

    python src/analyse.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import fetch_data
import profiles

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"

# A mid-size industrial customer: the lower end of Eurostat's 2 000-19 999 MWh band,
# which is the segment a B2B sales team spends most of its time on.
ANNUAL_CONSUMPTION_MWH = 2_000

# System sizes expressed as generation relative to consumption, which is how the
# sizing conversation with a customer actually goes ("cover a third of your usage")
# and which makes the result independent of the site's absolute size.
SIZING_RATIOS = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60]
BASE_RATIO = 0.30

# What a self-consumed kilowatt-hour actually avoids depends on the customer's
# tariff: network charges are partly capacity-based, and a capacity charge does not
# fall when consumption does. Rather than pick one answer, the model runs three and
# reports all of them.
AVOIDED_SCENARIOS = {
    "commodity_only": "Energy and supply only (network fully capacity-based)",
    "commodity_and_taxes": "Energy, taxes and levies (network fully capacity-based)",
    "full_retail": "The whole variable retail price, network included",
}

# European segment ranges for commercial rooftop (100 kW - 1 MW), used as a span
# rather than a point estimate. A real project is quoted, not benchmarked.
CAPEX_RANGE_EUR_PER_KWP = [700, 850, 1000, 1150, 1300]
# A hurdle, not a law of nature. Nine years sits inside the range this model
# actually produces (7.6 to 10.0 at 1 000 EUR/kWp), so it discriminates between
# profiles instead of rejecting or accepting all of them. The ranking is the
# durable result; the absolute years move with the quote and the tariff.
TARGET_PAYBACK_YEARS = 9


def main() -> None:
    pv = pd.read_csv(CLEAN / "pv_hourly.csv", encoding="utf-8-sig")
    prices = pd.read_csv(CLEAN / "prices_2023.csv", encoding="utf-8-sig")
    shape = pd.read_csv(CLEAN / "price_shape.csv", encoding="utf-8-sig")
    retail = pd.read_csv(CLEAN / "retail.csv", encoding="utf-8-sig")
    annual = pd.read_csv(CLEAN / "pv_annual.csv", encoding="utf-8-sig")

    year = fetch_data.ANALYSIS_YEAR
    retail_year = int(retail["year"].max())
    latest_retail = retail[retail["year"] == retail_year].iloc[0]

    avoided_price = {
        "commodity_only": float(latest_retail["energy_supply"]),
        "commodity_and_taxes": float(latest_retail["energy_supply"]
                                     + latest_retail["taxes_excl_vat"]),
        "full_retail": float(latest_retail["retail_excl_vat"]),
    }

    findings: dict[str, object] = {
        "meta": {
            "pv_source": "PVGIS (European Commission JRC), SARAH3, hourly",
            "price_source": "energy-charts.info (Fraunhofer ISE), CC BY 4.0",
            "retail_source": f"Eurostat nrg_pc_205_c, {retail_year}, band "
                             f"2 000-19 999 MWh, excluding VAT",
            "analysis_year": year,
            "annual_consumption_mwh": ANNUAL_CONSUMPTION_MWH,
            "system": "roof-mounted, 35 degrees, facing south, 14% system losses",
            "sizing_basis": "kWp sized against the PVGIS long-run average yield; the "
                            "hourly shape comes from the analysis year",
            "timezone": "Europe/Prague; PV and prices joined on the UTC hour",
        },
        "retail_components_eur_per_kwh": {
            "year": retail_year,
            "energy_supply": round(float(latest_retail["energy_supply"]), 4),
            "network": round(float(latest_retail["network"]), 4),
            "taxes_excl_vat": round(float(latest_retail["taxes_excl_vat"]), 4),
            "retail_excl_vat": round(float(latest_retail["retail_excl_vat"]), 4),
        },
        "avoided_price_eur_per_kwh": {k: round(v, 4) for k, v in avoided_price.items()},
        "avoided_scenarios": AVOIDED_SCENARIOS,
        "pv_resource": annual.to_dict("records"),
    }

    # ------------------------------------------------- 1. what export is worth
    # The PV shape by month and hour, applied to each year's prices. Solar output
    # does not care which weekday it is, so a month-hour shape captures it without
    # needing the PV and price years to line up.
    reference_key = annual.iloc[len(annual) // 2]["location"]     # median yield
    ref_pv = pv[pv["location"] == reference_key]
    pv_shape = (ref_pv.groupby(["month", "hour"])["kw_per_kwp"].mean()
                .rename("kw").reset_index())

    capture = {}
    for price_year, block in shape.groupby("year"):
        merged = pv_shape.merge(block, on=["month", "hour"], how="left")
        captured = float(np.average(merged["price_eur_mwh"], weights=merged["kw"]))
        baseload = float(block["year_baseload"].iloc[0])
        capture[int(price_year)] = {
            "capture_price_eur_mwh": round(captured, 2),
            "baseload_eur_mwh": round(baseload, 2),
            "capture_rate": round(captured / baseload, 4),
        }
    findings["capture_rate"] = {
        "reference_location": reference_key,
        "note": "Modelled estimate. A PVGIS generation shape for this location is "
                "weighted against that year's actual day-ahead prices and compared "
                "with the flat baseload price of the same year. Below 1.00 means "
                "solar generates when power is cheap. This is not metered output "
                "from an existing plant.",
        "by_year": capture,
    }

    # ------------------------------ 2. self-consumption by profile and system size
    price_series = prices.set_index("ts_utc_hour")["price_eur_mwh"]
    long_run_yield = dict(zip(annual["location"], annual["yield_kwh_per_kwp"]))

    def run(location: str, profile: profiles.LoadProfile,
            ratio: float) -> dict[str, float]:
        site = pv[pv["location"] == location].copy()
        site = site.sort_values("ts_utc_hour")
        weights = profile.weights(site["hour"], site["is_weekend"])
        load_kwh = weights / weights.sum() * (ANNUAL_CONSUMPTION_MWH * 1000)

        # The hourly series is one specific year; the kilowatt-peak a customer would
        # actually install is sized against the long-run average yield, because that
        # is what the system will produce over its life. So the 2023 shape is used
        # for *when* the energy arrives and the long-run yield for *how much a kWp
        # delivers*. Mixing the two -- sizing on one and looking up self-consumption
        # computed on the other -- is what made the workbook and the model disagree.
        shape = site["kw_per_kwp"].to_numpy() / site["kw_per_kwp"].sum()
        target_kwh = ANNUAL_CONSUMPTION_MWH * 1000 * ratio
        generation = shape * target_kwh
        kwp = target_kwh / long_run_yield[location]

        self_consumed = np.minimum(generation, np.asarray(load_kwh))
        exported = generation - self_consumed

        spot = site["ts_utc_hour"].map(price_series).to_numpy() / 1000   # EUR/kWh
        if np.isnan(spot).any():
            raise RuntimeError(f"{int(np.isnan(spot).sum())} hours have no price. "
                               f"A silent NaN here turns the annual revenue into NaN "
                               f"and every derived figure with it.")
        # Revenue in negative-price hours is floored at zero: an operator would
        # switch the inverter off rather than pay to export. The energy is still
        # counted as generated and exported; only its revenue is zeroed, so the
        # self-consumption rate is unaffected.
        export_revenue = float((exported * np.maximum(spot, 0)).sum())
        zero_revenue_export = float(exported[spot < 0].sum())

        return {
            "kwp": kwp,
            "generation_kwh": float(generation.sum()),
            "self_consumed_kwh": float(self_consumed.sum()),
            "exported_kwh": float(exported.sum()),
            "zero_revenue_export_kwh": zero_revenue_export,
            "self_consumption_rate": float(self_consumed.sum() / generation.sum()),
            "self_sufficiency_rate": float(self_consumed.sum()
                                           / np.asarray(load_kwh).sum()),
            "export_revenue_eur": export_revenue,
            "export_price_eur_per_kwh": (export_revenue / exported.sum()
                                         if exported.sum() > 0 else 0.0),
        }

    # The commercially useful question is not "does solar work for this customer"
    # -- at a small enough system it works for everybody, because everything is
    # self-consumed. It is "how large a system can this customer absorb before the
    # surplus stops being worth anything". That is what the grid below answers.
    BASE_CAPEX = 1000

    grid = {}
    for profile in profiles.PROFILES:
        grid[profile.key] = {}
        for ratio in SIZING_RATIOS:
            result = run(reference_key, profile, ratio)
            row = {
                "kwp": round(result["kwp"], 1),
                "generation_mwh": round(result["generation_kwh"] / 1000, 1),
                # Six decimals, not four: the workbook recomputes payback from these
                # published values, and rounding the rate and the export price to
                # four moved the answer by half a month. Precision is cheap here and
                # a spreadsheet that disagrees with the report is not.
                "self_consumption_rate": round(result["self_consumption_rate"], 6),
                "self_sufficiency_rate": round(result["self_sufficiency_rate"], 6),
                "exported_mwh": round(result["exported_kwh"] / 1000, 1),
                "zero_revenue_export_mwh": round(
                    result["zero_revenue_export_kwh"] / 1000, 2),
                "export_price_eur_per_kwh": round(
                    result["export_price_eur_per_kwh"], 6),
                "savings_eur": {},
                "payback_years": {},
            }
            for scenario, price in avoided_price.items():
                savings = (result["self_consumed_kwh"] * price
                           + result["export_revenue_eur"])
                row["savings_eur"][scenario] = round(savings, 0)
                # Two decimals in the stored value, one on screen. Rounding to a
                # tenth here and then checking the workbook against it makes a
                # correct spreadsheet look like a broken one.
                row["payback_years"][scenario] = round(
                    BASE_CAPEX * result["kwp"] / savings, 2)
            grid[profile.key][f"{ratio:.2f}"] = row

    findings["sizing"] = {
        "location": reference_key,
        "ratios": SIZING_RATIOS,
        "base_ratio": BASE_RATIO,
        "base_capex_eur_per_kwp": BASE_CAPEX,
        "by_profile": grid,
    }

    # ------------------------------ 3. the largest system that still pays back
    largest = {}
    for profile in profiles.PROFILES:
        block = grid[profile.key]
        viable = [r for r in SIZING_RATIOS
                  if block[f"{r:.2f}"]["payback_years"]["commodity_and_taxes"]
                  <= TARGET_PAYBACK_YEARS]
        best_ratio = max(viable) if viable else None
        largest[profile.key] = {
            "profile": profile.name,
            "typical_customer": profile.typical_customer,
            "max_ratio_within_target": best_ratio,
            "max_kwp": (block[f"{best_ratio:.2f}"]["kwp"] if best_ratio else None),
            "self_consumption_at_max": (
                block[f"{best_ratio:.2f}"]["self_consumption_rate"]
                if best_ratio else None),
            "savings_at_max_eur": (
                block[f"{best_ratio:.2f}"]["savings_eur"]["commodity_and_taxes"]
                if best_ratio else None),
        }
    findings["largest_viable_system"] = {
        "target_payback_years": TARGET_PAYBACK_YEARS,
        "capex_eur_per_kwp": BASE_CAPEX,
        "avoided_scenario": "commodity_and_taxes",
        "note": "Simple payback, undiscounted, at a single capex point. The ranking "
                "between profiles is what matters here; the absolute years move with "
                "the quote.",
        "by_profile": largest,
    }

    # ------------------------------------------- the base case, per profile
    base = {}
    for profile in profiles.PROFILES:
        row = dict(grid[profile.key][f"{BASE_RATIO:.2f}"])
        result_kwp = row["kwp"]
        row["payback_by_capex"] = {
            scenario: {str(capex): round(capex * result_kwp
                                         / row["savings_eur"][scenario], 1)
                       for capex in CAPEX_RANGE_EUR_PER_KWP}
            for scenario in avoided_price
        }
        row["break_even_capex_eur_per_kwp"] = {
            scenario: round(row["savings_eur"][scenario] * TARGET_PAYBACK_YEARS
                            / result_kwp, 0)
            for scenario in avoided_price
        }
        base[profile.key] = row

    findings["base_case"] = {
        "location": reference_key,
        "sizing_ratio": BASE_RATIO,
        "capex_range_eur_per_kwp": CAPEX_RANGE_EUR_PER_KWP,
        "target_payback_years": TARGET_PAYBACK_YEARS,
        "by_profile": base,
    }

    # ------------------------------------------------------- 4. by location
    by_location = {}
    office = profiles.BY_KEY["office"]
    for location in annual["location"]:
        result = run(location, office, BASE_RATIO)
        savings = (result["self_consumed_kwh"] * avoided_price["commodity_and_taxes"]
                   + result["export_revenue_eur"])
        by_location[location] = {
            "yield_kwh_per_kwp": float(
                annual.loc[annual["location"] == location, "yield_kwh_per_kwp"].iloc[0]),
            "self_consumption_rate": round(result["self_consumption_rate"], 4),
            "savings_eur": round(savings, 0),
            "payback_years_at_1000": round(1000 * result["kwp"] / savings, 1),
        }
    findings["by_location"] = {
        "profile": office.name,
        "sizing_ratio": BASE_RATIO,
        "avoided_scenario": "commodity_and_taxes",
        "results": by_location,
    }

    # ------------------------------------ 4b. what an average June day looks like
    # The tables say what the overlap is worth; this shows what it looks like on a
    # single day.
    site = pv[pv["location"] == reference_key].sort_values("ts_utc_hour")
    # Weekdays only: blending in the weekend would flatten the plateau of every
    # weekday profile and make the picture agree with no actual day of the week.
    june = site[(site["month"] == 6) & (~site["is_weekend"])]
    ratio_kwp = (ANNUAL_CONSUMPTION_MWH * 1000 * BASE_RATIO) / site["kw_per_kwp"].sum()
    generation_day = (june.groupby("hour")["kw_per_kwp"].mean() * ratio_kwp).round(1)

    typical_day = {"generation_kw": {int(h): float(v)
                                     for h, v in generation_day.items()}}
    for profile in profiles.PROFILES:
        weights = profile.weights(site["hour"], site["is_weekend"])
        load = pd.Series(np.asarray(weights) / np.asarray(weights).sum()
                         * (ANNUAL_CONSUMPTION_MWH * 1000), index=site.index)
        june_load = load.loc[june.index].groupby(june["hour"]).mean().round(1)
        typical_day[profile.key] = {int(h): float(v) for h, v in june_load.items()}
    findings["typical_june_day"] = {
        "location": reference_key,
        "sizing_ratio": BASE_RATIO,
        "kwp": round(ratio_kwp, 1),
        "note": "Average June weekday, hourly means in kW.",
        "series": typical_day,
    }

    # ------------------------------------------------- 5. the headline
    small, large = "0.10", "0.60"
    spread_small = {k: grid[k][small]["self_consumption_rate"] for k in grid}
    spread_large = {k: grid[k][large]["self_consumption_rate"] for k in grid}
    best = max(spread_large, key=spread_large.get)
    worst = min(spread_large, key=spread_large.get)

    findings["headline"] = {
        "small_system_ratio": float(small),
        "large_system_ratio": float(large),
        "spread_at_small_pp": round((max(spread_small.values())
                                     - min(spread_small.values())) * 100, 1),
        "spread_at_large_pp": round((spread_large[best] - spread_large[worst]) * 100, 1),
        "best_profile": profiles.BY_KEY[best].name,
        "best_self_consumption_pct": round(spread_large[best] * 100, 1),
        "worst_profile": profiles.BY_KEY[worst].name,
        "worst_self_consumption_pct": round(spread_large[worst] * 100, 1),
        "max_kwp_best": largest[best]["max_kwp"],
        "max_kwp_worst": largest[worst]["max_kwp"],
        "size_ratio_best_to_worst": (
            round(largest[best]["max_kwp"] / largest[worst]["max_kwp"], 2)
            if largest[best]["max_kwp"] and largest[worst]["max_kwp"] else None),
        "retail_vs_export_ratio": round(
            avoided_price["commodity_and_taxes"]
            / base[best]["export_price_eur_per_kwh"], 2),
        "capture_rate_first": capture[min(capture)]["capture_rate"],
        "capture_rate_last": capture[max(capture)]["capture_rate"],
        "capture_years": [min(capture), max(capture)],
    }

    (CLEAN / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------ report
    head = findings["headline"]
    print(f"Reference location: {reference_key} (median yield of the five)")
    print(f"Site: {ANNUAL_CONSUMPTION_MWH:,} MWh/year\n")
    print("Self-consumption rate by system size (generation as % of consumption):")
    header = "".join(f"{int(r * 100):>7}%" for r in SIZING_RATIOS)
    print(f"{'profile':<34}{header}")
    for profile in profiles.PROFILES:
        block = grid[profile.key]
        line = "".join(f"{block[f'{r:.2f}']['self_consumption_rate'] * 100:>7.1f}%"
                       for r in SIZING_RATIOS)
        print(f"{profile.name:<34}{line}")

    print(f"\n1. At a system covering {head['small_system_ratio']:.0%} of consumption "
          f"the profiles differ by only {head['spread_at_small_pp']} points. "
          f"At {head['large_system_ratio']:.0%} they differ by "
          f"{head['spread_at_large_pp']}.")
    print(f"2. Within a {TARGET_PAYBACK_YEARS}-year payback at "
          f"{findings['largest_viable_system']['capex_eur_per_kwp']} EUR/kWp, "
          f"{head['best_profile']} supports {head['max_kwp_best']:,.0f} kWp against "
          f"{head['max_kwp_worst']:,.0f} kWp for {head['worst_profile']} "
          f"({head['size_ratio_best_to_worst']}x).")
    print(f"3. A self-consumed kWh is worth {head['retail_vs_export_ratio']}x an "
          f"exported one.")
    print(f"4. Solar's wholesale capture rate fell from "
          f"{head['capture_rate_first']:.2f} to {head['capture_rate_last']:.2f} of "
          f"baseload between {head['capture_years'][0]} and {head['capture_years'][1]}, "
          f"so that gap is widening.")
    print(f"\nWrote {(CLEAN / 'findings.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
