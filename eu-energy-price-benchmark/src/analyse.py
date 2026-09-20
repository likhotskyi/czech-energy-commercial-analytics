"""
Step 3: compute every number the report, the workbook and the deck will quote,
once, into `data/clean/findings.json`.

Nothing downstream recalculates anything and no figure is ever typed by hand. If
Eurostat revises a series, one run updates the text, the charts, the spreadsheet
and the slides together -- and they cannot disagree with each other, which is the
usual way a monthly report ends up embarrassing somebody.

    python src/analyse.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"

FOCUS_BAND = "MWH2000-19999"
FOCUS_BAND_NAME = "2 000-19 999 MWh"
HOME = "Czechia"
REFERENCE = "EU average"

# A supplier competes on the energy & supply component. Network charges are set
# by the regulator and taxes by the state: the same for every supplier, on every
# offer, in that country.
ILLUSTRATIVE_DISCOUNT = 0.10


def pct(value: float) -> float:
    return round(value * 100, 1)


def main() -> None:
    elec = pd.read_csv(CLEAN / "electricity_prices.csv", encoding="utf-8-sig")
    gas = pd.read_csv(CLEAN / "gas_prices.csv", encoding="utf-8-sig")
    comp = pd.read_csv(CLEAN / "price_components.csv", encoding="utf-8-sig")
    source = json.loads((CLEAN / "source.json").read_text(encoding="utf-8"))

    band = elec[elec["nrg_cons"] == FOCUS_BAND].copy()
    latest_period = band["period"].max()
    latest = band[band["period"] == latest_period].set_index("country")["price_eur_per_unit"]

    peers = latest.drop(REFERENCE).sort_values()
    cz_price = float(latest[HOME])
    eu_price = float(latest[REFERENCE])

    findings: dict[str, object] = {
        "meta": {
            "source": "Eurostat",
            "last_updated_by_eurostat": source["last_updated_by_eurostat"],
            "tax_basis": source["tax_basis"],
            "band": FOCUS_BAND_NAME,
            "latest_period": latest_period,
            "countries": list(latest.index),
        }
    }

    # ---------------------------------------------------------- 1. price level
    ranking = [{"country": c, "price": round(float(p), 4)} for c, p in peers.items()]
    findings["price_level"] = {
        "period": latest_period,
        "czechia": round(cz_price, 4),
        "eu_average": round(eu_price, 4),
        "gap_vs_eu_pct": pct(cz_price / eu_price - 1),
        "rank_among_peers": int(list(peers.index).index(HOME)) + 1,
        "peer_count": len(peers),
        "cheapest_peer": peers.index[0],
        "most_expensive_peer": peers.index[-1],
        "gap_vs_germany_pct": pct(cz_price / float(latest["Germany"]) - 1),
        "gap_vs_poland_pct": pct(cz_price / float(latest["Poland"]) - 1),
        "ranking": ranking,
    }

    # ------------------------------------------------------ 2. what the bill is
    latest_year = int(comp["year"].max())
    recent = comp[comp["year"] == latest_year].set_index("country")
    cz = recent.loc[HOME]

    composition = [{
        "country": country,
        "energy_supply": round(float(row["energy_supply"]), 4),
        "network_costs": round(float(row["network_costs"]), 4),
        "taxes_excl_vat": round(float(row["taxes_excl_vat"]), 4),
        "total": round(float(row["total_excl_vat"]), 4),
        "share_energy_supply_pct": pct(float(row["share_energy_supply"])),
        "share_network_pct": pct(float(row["share_network"])),
        "share_taxes_pct": pct(float(row["share_taxes"])),
    } for country, row in recent.iterrows()]
    composition.sort(key=lambda r: r["share_energy_supply_pct"], reverse=True)

    cz_share = float(cz["share_energy_supply"])
    peer_shares = recent.drop(REFERENCE)["share_energy_supply"]
    findings["composition"] = {
        "year": latest_year,
        "czechia_share_energy_supply_pct": pct(cz_share),
        "czechia_share_network_pct": pct(float(cz["share_network"])),
        "czechia_share_taxes_pct": pct(float(cz["share_taxes"])),
        "eu_share_energy_supply_pct": pct(float(recent.loc[REFERENCE, "share_energy_supply"])),
        "czechia_rank_by_addressable_share": int(
            peer_shares.rank(ascending=False)[HOME]),
        "peer_count": len(peer_shares),
        "lowest_addressable": {
            "country": peer_shares.idxmin(),
            "share_pct": pct(float(peer_shares.min())),
        },
        "by_country": composition,
    }

    # --------------------------------------- 3. what a discount is actually worth
    discount_effect = []
    for country, row in recent.iterrows():
        effect = ILLUSTRATIVE_DISCOUNT * float(row["share_energy_supply"])
        discount_effect.append({
            "country": country,
            "bill_reduction_pct": pct(effect),
            "eur_per_mwh": round(ILLUSTRATIVE_DISCOUNT * float(row["energy_supply"]) * 1000, 2),
        })
    discount_effect.sort(key=lambda r: r["bill_reduction_pct"], reverse=True)
    findings["discount_leverage"] = {
        "discount_on_commodity_pct": pct(ILLUSTRATIVE_DISCOUNT),
        "czechia_bill_reduction_pct": pct(ILLUSTRATIVE_DISCOUNT * cz_share),
        "germany_bill_reduction_pct": pct(
            ILLUSTRATIVE_DISCOUNT * float(recent.loc["Germany", "share_energy_supply"])),
        "by_country": discount_effect,
    }

    # ------------------------------------------------------- 4. size discount
    latest_bands = elec[(elec["period"] == latest_period)]
    band_table = latest_bands.pivot_table(index="band", columns="country",
                                          values="price_eur_per_unit")
    order = ["< 20 MWh", "20-499 MWh", "500-1 999 MWh", "2 000-19 999 MWh",
             "20 000-69 999 MWh", "70 000-149 999 MWh", ">= 150 000 MWh"]
    band_table = band_table.reindex([b for b in order if b in band_table.index])

    # Comparing each country's *last available* band would compare different bands:
    # Czechia publishes nothing for >= 150 000 MWh (too few consumers to report
    # without disclosing them), so its "largest band" is one step down from
    # Germany's. The size discount is therefore measured between the smallest band
    # and the largest band that every country in the comparison actually reports.
    complete = [b for b in band_table.index if band_table.loc[b].notna().all()]
    if len(complete) < 2:
        raise RuntimeError("No two consumption bands are reported by every country.")
    small_band, large_band = complete[0], complete[-1]

    discounts = {c: float(band_table.loc[large_band, c] / band_table.loc[small_band, c] - 1)
                 for c in band_table.columns}

    # Flag any country whose price curve turns back up at the top: that is either a
    # real tariff quirk or a thin sample, and either way it should not pass silently.
    anomalies = []
    for country in band_table.columns:
        series = band_table[country].dropna()
        rises = [(series.index[i - 1], series.index[i])
                 for i in range(1, len(series)) if series.iloc[i] > series.iloc[i - 1]]
        if rises:
            anomalies.append({"country": country,
                              "rises_between": [f"{a} -> {b}" for a, b in rises]})

    incomplete = {b: [c for c in band_table.columns if pd.isna(band_table.loc[b, c])]
                  for b in band_table.index}
    findings["size_discount"] = {
        "period": latest_period,
        "measured_between": {"from": small_band, "to": large_band},
        "reason_for_band_choice":
            f"'{large_band}' is the largest band every country in the comparison "
            f"reports; using each country's own largest band would compare "
            f"different bands.",
        "czechia_smallest_band_price": round(float(band_table.loc[small_band, HOME]), 4),
        "czechia_largest_band_price": round(float(band_table.loc[large_band, HOME]), 4),
        "czechia_discount_pct": pct(discounts[HOME]),
        "eu_discount_pct": pct(discounts[REFERENCE]),
        "by_country": {c: pct(v) for c, v in discounts.items()},
        "bands_not_reported_by_all": {b: cs for b, cs in incomplete.items() if cs},
        "non_monotonic_curves": anomalies,
        "table": {band: {c: (None if pd.isna(v) else round(float(v), 4))
                         for c, v in row.items()}
                  for band, row in band_table.iterrows()},
    }

    # ---------------------------------------------------------- 5. the shock
    cz_series = band[band["country"] == HOME].sort_values("period_start")
    pre_crisis = cz_series[cz_series["period"] == "2021-S2"]["price_eur_per_unit"]
    peak_row = cz_series.loc[cz_series["price_eur_per_unit"].idxmax()]
    findings["price_shock"] = {
        "pre_crisis_period": "2021-S2",
        "pre_crisis_price": round(float(pre_crisis.iloc[0]), 4) if len(pre_crisis) else None,
        "peak_period": peak_row["period"],
        "peak_price": round(float(peak_row["price_eur_per_unit"]), 4),
        "rise_to_peak_pct": pct(float(peak_row["price_eur_per_unit"]) / float(pre_crisis.iloc[0]) - 1)
                            if len(pre_crisis) else None,
        "latest_price": round(cz_price, 4),
        "fall_from_peak_pct": pct(cz_price / float(peak_row["price_eur_per_unit"]) - 1),
        "vs_pre_crisis_pct": pct(cz_price / float(pre_crisis.iloc[0]) - 1) if len(pre_crisis) else None,
    }

    # ------------------------------------------------------------------ 6. gas
    gas_band = gas[gas["nrg_cons"] == "GJ10000-99999"]
    gas_latest_period = gas_band["period"].max()
    gas_latest = (gas_band[gas_band["period"] == gas_latest_period]
                  .set_index("country")["price_eur_per_unit"])
    gas_peers = gas_latest.drop(REFERENCE).sort_values()
    findings["gas"] = {
        "period": gas_latest_period,
        "band": "10 000-99 999 GJ",
        "czechia": round(float(gas_latest[HOME]), 4),
        "eu_average": round(float(gas_latest[REFERENCE]), 4),
        "gap_vs_eu_pct": pct(float(gas_latest[HOME]) / float(gas_latest[REFERENCE]) - 1),
        "rank_among_peers": int(list(gas_peers.index).index(HOME)) + 1,
        "peer_count": len(gas_peers),
        "ranking": [{"country": c, "price": round(float(p), 4)} for c, p in gas_peers.items()],
    }

    # --------------------------------------------------------- 7. data quality
    recon = pd.read_csv(CLEAN / "reconciliation.csv", encoding="utf-8-sig")
    findings["data_quality"] = {
        "observations_electricity": int(len(elec)),
        "observations_gas": int(len(gas)),
        "component_years": int(comp["year"].nunique()),
        "reconciliation_median_deviation_pct": round(
            float(recon["deviation_pct"].abs().median()), 2),
        "naive_method_median_deviation_pct": round(
            float(recon["naive_deviation_pct"].abs().median()), 2),
        "missing_observations": int(
            len(elec) - elec["price_eur_per_unit"].notna().sum()),
    }

    (CLEAN / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

    p = findings["price_level"]
    c = findings["composition"]
    d = findings["discount_leverage"]
    s = findings["size_discount"]
    k = findings["price_shock"]
    print(f"Period {p['period']}, band {FOCUS_BAND_NAME}, excluding VAT\n")
    print(f"1. Czechia pays {p['czechia']} EUR/kWh: {p['gap_vs_eu_pct']:+}% vs the EU average, "
          f"{p['gap_vs_germany_pct']:+}% vs Germany.")
    print(f"   Rank {p['rank_among_peers']} of {p['peer_count']} neighbours "
          f"(cheapest: {p['cheapest_peer']}, dearest: {p['most_expensive_peer']}).")
    print(f"2. {c['czechia_share_energy_supply_pct']}% of a Czech industrial bill is the "
          f"commodity -- rank {c['czechia_rank_by_addressable_share']} of {c['peer_count']} "
          f"(EU average {c['eu_share_energy_supply_pct']}%, "
          f"{c['lowest_addressable']['country']} only {c['lowest_addressable']['share_pct']}%).")
    print(f"3. A {d['discount_on_commodity_pct']}% cut on the commodity moves a Czech "
          f"customer's total bill by {d['czechia_bill_reduction_pct']}% "
          f"(Germany: {d['germany_bill_reduction_pct']}%).")
    print(f"4. In Czechia the largest consumption band pays {abs(s['czechia_discount_pct'])}% "
          f"less per kWh than the smallest; across the EU the same gap is "
          f"{abs(s['eu_discount_pct'])}%.")
    print(f"5. Prices peaked in {k['peak_period']} at {k['peak_price']} "
          f"({k['rise_to_peak_pct']:+}% on 2021-S2); now {k['fall_from_peak_pct']:+}% off the peak "
          f"but still {k['vs_pre_crisis_pct']:+}% above pre-crisis.")
    print(f"\nWrote {(CLEAN / 'findings.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
