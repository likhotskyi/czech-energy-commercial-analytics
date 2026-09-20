"""
Step 1: download everything and cache the raw responses.

    python src/fetch_data.py [--refresh]

Five Czech locations, chosen to span the country's industrial geography rather
than its sunniest corners: the coordinates are city centres, used as a stand-in
for "an industrial site in this region". Sub-kilometre precision would be false
accuracy — the irradiance grid is coarser than that, and a real project uses the
roof's own coordinates, orientation and shading survey.

The analysis year is 2023: the most recent year for which PVGIS publishes hourly
output. Pairing generation and prices from the same hours of the same year matters,
because the value of an exported kilowatt-hour depends on what the price was doing
at the moment the sun was shining.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import sources

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

ANALYSIS_YEAR = 2023          # latest year PVGIS publishes hourly series for
# Price years used for the capture-rate trend. 2026 is excluded: it is not a
# complete year, and an average over January-August would compare a partial year
# against full ones.
PRICE_YEARS = [2021, 2022, 2023, 2024, 2025]

LOCATIONS = [
    {"key": "praha", "name": "Prague", "region": "Praha",
     "lat": 50.075, "lon": 14.437},
    {"key": "plzen", "name": "Plzeň", "region": "Plzeňský",
     "lat": 49.747, "lon": 13.377},
    {"key": "usti", "name": "Ústí nad Labem", "region": "Ústecký",
     "lat": 50.661, "lon": 14.032},
    {"key": "brno", "name": "Brno", "region": "Jihomoravský",
     "lat": 49.195, "lon": 16.606},
    {"key": "ostrava", "name": "Ostrava", "region": "Moravskoslezský",
     "lat": 49.820, "lon": 18.262},
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    print(f"{'location':<18}{'kWh/kWp/yr':>12}{'st.dev':>9}{'hourly pts':>12}")
    for location in LOCATIONS:
        annual = sources.cached(
            RAW / f"pv_annual_{location['key']}.json",
            sources.pv_annual_url(location["lat"], location["lon"]), args.refresh)
        hourly = sources.cached(
            RAW / f"pv_hourly_{location['key']}_{ANALYSIS_YEAR}.json",
            sources.pv_hourly_url(location["lat"], location["lon"], ANALYSIS_YEAR),
            args.refresh)

        totals = annual["outputs"]["totals"]["fixed"]
        points = len(hourly["outputs"]["hourly"])
        if points not in (8760, 8784):
            raise RuntimeError(f"{location['name']}: {points} hourly points, "
                               f"expected a full year")
        print(f"{location['name']:<18}{totals['E_y']:>12.0f}"
              f"{totals['SD_y']:>9.1f}{points:>12,}")

    db = annual["inputs"]["meteo_data"]
    print(f"\nPVGIS radiation database {db['radiation_db']}, "
          f"covering {db['year_min']}-{db['year_max']}. "
          f"Hourly series taken for {ANALYSIS_YEAR}.")
    print("Yields are for 1 kWp, roof-mounted, 35 degrees, facing south, "
          "14% system losses.\n")

    for year in PRICE_YEARS:
        prices = sources.cached(RAW / f"day_ahead_CZ_{year}.json",
                                sources.price_url(year), args.refresh)
        values = [p for p in prices["price"] if p is not None]
        print(f"Day-ahead prices {year}: {len(prices['price']):,} settlement "
              f"periods, mean {sum(values) / len(values):.1f} EUR/MWh "
              f"({prices.get('license_info', '')[:22]})")

    retail = sources.cached(RAW / "retail_components_CZ.json",
                            sources.retail_components_url(), args.refresh)
    print(f"\nEurostat retail components: {retail.get('label', '')}, "
          f"updated {retail.get('updated', '')[:10]}")


if __name__ == "__main__":
    main()
