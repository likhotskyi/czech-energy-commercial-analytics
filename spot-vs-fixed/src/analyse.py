"""
Step 3: compute every number the workbook, the deck and the report will quote,
once, into data/clean/findings.json.

The central quantity is the **profile factor**: what a customer's own consumption
shape does to the average price it pays on a spot-indexed contract.

    profile factor = (sum of price x load x duration) / (sum of load x duration)
                     -------------------------------------------------------
                                    baseload price

A factor of 1.00 means the customer's shape is neutral: it consumes the market
average. Above 1.00 it consumes when power is expensive; below, when it is cheap.

What the factor is NOT: a full comparison of a spot product against a fixed one.
A real fixed offer is a forward price plus a risk premium and a balancing charge,
none of which are in public data. The factor isolates the *shape* effect, which is
the part that differs between two customers buying the same volume from the same
supplier in the same year. Stated that way it is a defensible number; stated as
"spot is X% cheaper" it would not be.

    python src/analyse.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import profiles

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"

EXAMPLE_VOLUME_MWH = 10_000          # 10 GWh/year: a mid-size industrial customer
SUMMER = [5, 6, 7, 8]                # May-August
WINTER = [11, 12, 1, 2]              # November-February


def wmean(values: pd.Series, weights) -> float:
    return float(np.average(values, weights=weights))


def main() -> None:
    df = pd.read_csv(CLEAN / "prices.csv", encoding="utf-8-sig")
    coverage = pd.read_csv(CLEAN / "coverage.csv", encoding="utf-8-sig")

    complete_years = coverage.loc[coverage["status"] == "complete year", "year"].tolist()
    partial_years = coverage.loc[coverage["status"] == "partial year", "year"].tolist()
    all_years = sorted(df["year"].unique())
    latest_year = int(max(all_years))

    findings: dict[str, object] = {
        "meta": {
            "source": "energy-charts.info (Fraunhofer ISE), day-ahead auction",
            "licence": "CC BY 4.0",
            "bidding_zone": "CZ",
            "currency_unit": "EUR/MWh",
            "timezone": "Europe/Prague (local), converted from UTC",
            "years_complete": [int(y) for y in complete_years],
            "years_partial": [int(y) for y in partial_years],
            "latest_year": latest_year,
            "settlement_periods": int(len(df)),
            "resolution_note": "Hourly until 30 September 2025, 15-minute from "
                               "1 October 2025. All averages are duration-weighted.",
        }
    }

    # ------------------------------------------------------------- baseload
    # Keep the unrounded value for arithmetic and round only for display: dividing
    # by a rounded baseload makes the flat 24/7 profile come out at 0.9999 instead
    # of exactly 1.000, which is wrong by definition and invites doubt about the
    # rest of the table.
    baseload_exact = {int(y): wmean(g["price_eur_mwh"], g["duration_h"])
                      for y, g in df.groupby("year")}
    baseload = {y: round(v, 2) for y, v in baseload_exact.items()}
    findings["baseload"] = baseload

    # -------------------------------------------------------- intraday shape
    intraday = {}
    for year, g in df.groupby("year"):
        by_hour = {int(h): round(wmean(sub["price_eur_mwh"], sub["duration_h"]), 1)
                   for h, sub in g.groupby("hour_local")}
        cheapest = min(by_hour, key=by_hour.get)
        dearest = max(by_hour, key=by_hour.get)
        intraday[int(year)] = {
            "by_hour": by_hour,
            "cheapest_hour": cheapest,
            "cheapest_price": by_hour[cheapest],
            "most_expensive_hour": dearest,
            "most_expensive_price": by_hour[dearest],
            "midday_vs_night_pct": round(
                (np.mean([by_hour[h] for h in (11, 12, 13, 14)])
                 / np.mean([by_hour[h] for h in (1, 2, 3, 4)]) - 1) * 100, 1),
        }
    # The price level moved enormously between these years (2022 averaged 2.5x
    # 2024), so raw hourly prices cannot be compared across years on one axis.
    # Indexing each hour to its own year's baseload isolates the *shape*, which is
    # the thing this project is actually about.
    for year, block in intraday.items():
        base = baseload_exact[year]
        block["index_to_baseload"] = {h: round(p / base * 100, 1)
                                      for h, p in block["by_hour"].items()}
    findings["intraday"] = intraday

    # -------------------------------------------------------- profile factors
    factors: dict[str, dict[int, float]] = {}
    effective: dict[str, dict[int, float]] = {}
    naive_factors: dict[str, dict[int, float]] = {}

    for profile in profiles.PROFILES:
        factors[profile.key] = {}
        effective[profile.key] = {}
        naive_factors[profile.key] = {}
        for year, g in df.groupby("year"):
            base = baseload_exact[int(year)]
            weights = profile.weights(g["hour_local"], g["is_weekend"]) * g["duration_h"]
            price = wmean(g["price_eur_mwh"], weights)
            factors[profile.key][int(year)] = round(price / base, 4)
            effective[profile.key][int(year)] = round(price, 2)

            # Sensitivity: the same profile with the base load switched off. This
            # is the shape most people draw when they sketch a load curve, and it
            # is worth knowing how much of the result depends on that assumption.
            naive = profiles.LoadProfile(
                key=profile.key, name=profile.name, description="",
                operating_hours=profile.operating_hours,
                operating_days=profile.operating_days,
                base_load=0.0 if profile.base_load < 1 else 1.0,
                weekend_load=0.0 if profile.weekend_load < 1 else 1.0,
                typical_customer="")
            nweights = naive.weights(g["hour_local"], g["is_weekend"]) * g["duration_h"]
            if nweights.sum() > 0:
                naive_factors[profile.key][int(year)] = round(
                    wmean(g["price_eur_mwh"], nweights) / base, 4)

    findings["profile_factors"] = factors
    findings["effective_price"] = effective
    findings["profile_factors_without_base_load"] = naive_factors
    findings["profile_definitions"] = profiles.profile_table().to_dict("records")

    # --------------------------------------------------------- the inversion
    def crossing_year(series: dict[int, float], rising: bool) -> int | None:
        years = sorted(series)
        for a, b in zip(years, years[1:]):
            if rising and series[a] < 1 <= series[b]:
                return b
            if not rising and series[a] >= 1 > series[b]:
                return b
        return None

    office = factors["office"]
    night = factors["night_heavy"]
    first_year, last_year = int(min(all_years)), latest_year
    findings["inversion"] = {
        "office_first_year": office[first_year],
        "office_latest_year": office[last_year],
        "office_swing_pp": round((office[last_year] - office[first_year]) * 100, 1),
        "office_crosses_below_baseload_in": crossing_year(office, rising=False),
        "night_first_year": night[first_year],
        "night_latest_year": night[last_year],
        "night_swing_pp": round((night[last_year] - night[first_year]) * 100, 1),
        "night_crosses_above_baseload_in": crossing_year(night, rising=True),
        "gap_first_year_pp": round((night[first_year] - office[first_year]) * 100, 1),
        "gap_latest_year_pp": round((night[last_year] - office[last_year]) * 100, 1),
        "first_year": first_year,
        "last_year": last_year,
    }

    # ------------------------------------------------- spread between customers
    spreads = {}
    for year in all_years:
        year_factors = {k: v[int(year)] for k, v in factors.items()}
        best = min(year_factors, key=year_factors.get)
        worst = max(year_factors, key=year_factors.get)
        base = baseload_exact[int(year)]
        spread_eur = (year_factors[worst] - year_factors[best]) * base
        spreads[int(year)] = {
            "best_profile": profiles.BY_KEY[best].name,
            "best_factor": year_factors[best],
            "worst_profile": profiles.BY_KEY[worst].name,
            "worst_factor": year_factors[worst],
            "spread_pp": round((year_factors[worst] - year_factors[best]) * 100, 1),
            "spread_eur_per_mwh": round(spread_eur, 2),
            "spread_eur_per_year_at_example_volume": round(
                spread_eur * EXAMPLE_VOLUME_MWH, 0),
        }
    findings["customer_spread"] = {
        "example_volume_mwh": EXAMPLE_VOLUME_MWH,
        "by_year": spreads,
    }

    # -------------------------------------------------------------- seasonality
    seasonal = {}
    latest = df[df["year"] == latest_year]
    for profile in profiles.PROFILES:
        row = {}
        for label, months in (("summer", SUMMER), ("winter", WINTER)):
            season = latest[latest["month"].isin(months)]
            if season.empty:
                continue
            base = wmean(season["price_eur_mwh"], season["duration_h"])
            weights = (profile.weights(season["hour_local"], season["is_weekend"])
                       * season["duration_h"])
            row[label] = round(wmean(season["price_eur_mwh"], weights) / base, 4)
        seasonal[profile.key] = row
    findings["seasonality"] = {
        "year": latest_year,
        "summer_months": SUMMER,
        "winter_months": WINTER,
        "note": "Factors are relative to the baseload price of the same season, so "
                "they isolate shape from the seasonal level of prices.",
        "by_profile": seasonal,
    }

    # -------------------------------------------------------------- volatility
    volatility = {}
    for year, g in df.groupby("year"):
        mean = wmean(g["price_eur_mwh"], g["duration_h"])
        sd = float(np.sqrt(np.average((g["price_eur_mwh"] - mean) ** 2,
                                      weights=g["duration_h"])))
        daily = g.groupby("date_local")["price_eur_mwh"].agg(lambda s: s.max() - s.min())
        volatility[int(year)] = {
            "mean": round(mean, 2),
            "std_dev": round(sd, 2),
            "coefficient_of_variation": round(sd / mean, 3),
            "mean_daily_spread": round(float(daily.mean()), 1),
            "worst_day_spread": round(float(daily.max()), 1),
        }
    findings["volatility"] = volatility

    # ---------------------------------------------------------- negative prices
    negative = {}
    for year, g in df.groupby("year"):
        neg = g[g["negative"]]
        hours = float(neg["duration_h"].sum())
        by_hour = {int(h): round(float(sub["duration_h"].sum()), 1)
                   for h, sub in neg.groupby("hour_local")} if not neg.empty else {}
        negative[int(year)] = {
            "hours": round(hours, 1),
            "share_of_year_pct": round(hours / float(g["duration_h"].sum()) * 100, 2),
            "lowest_price": round(float(g["price_eur_mwh"].min()), 1),
            "hours_by_hour_of_day": by_hour,
        }
    findings["negative_prices"] = negative

    # -------------------------------------------------------------- data quality
    findings["data_quality"] = {
        "coverage": coverage.to_dict("records"),
        "settlement_periods": int(len(df)),
        "missing_prices": int(df["price_eur_mwh"].isna().sum()),
    }

    (CLEAN / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------ report
    inv = findings["inversion"]
    spread_latest = spreads[latest_year]
    print(f"Czech day-ahead prices, {first_year}-{latest_year} "
          f"({len(df):,} settlement periods)\n")
    print("Profile factor (1.00 = baseload):")
    table = pd.DataFrame({profiles.BY_KEY[k].name: v for k, v in factors.items()}).T
    print(table.to_string())
    print(f"\n1. The daytime office profile went from {inv['office_first_year']:.3f} "
          f"in {first_year} to {inv['office_latest_year']:.3f} in {latest_year} "
          f"({inv['office_swing_pp']:+} points).")
    print(f"   It fell below baseload in {inv['office_crosses_below_baseload_in']}.")
    print(f"2. The night-heavy profile went the other way: "
          f"{inv['night_first_year']:.3f} to {inv['night_latest_year']:.3f} "
          f"({inv['night_swing_pp']:+} points), crossing above baseload in "
          f"{inv['night_crosses_above_baseload_in']}.")
    print(f"3. In {first_year} the night profile was {abs(inv['gap_first_year_pp'])} "
          f"points cheaper than the office profile. In {latest_year} it is "
          f"{abs(inv['gap_latest_year_pp'])} points more expensive.")
    print(f"4. Between the best and worst shape in {latest_year} there is "
          f"{spread_latest['spread_pp']} points = "
          f"{spread_latest['spread_eur_per_mwh']} EUR/MWh, or "
          f"{spread_latest['spread_eur_per_year_at_example_volume']:,.0f} EUR a year "
          f"for a {EXAMPLE_VOLUME_MWH:,} MWh customer.")
    print(f"5. Midday is now {abs(intraday[latest_year]['midday_vs_night_pct'])}% "
          f"{'below' if intraday[latest_year]['midday_vs_night_pct'] < 0 else 'above'} "
          f"the small hours; in {first_year} it was "
          f"{intraday[first_year]['midday_vs_night_pct']:+}%.")
    print(f"\nWrote {(CLEAN / 'findings.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
