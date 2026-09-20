"""
Step 1: pull the source data from Eurostat and cache the raw responses.

    python src/fetch_data.py [--refresh]

Four datasets, chosen deliberately:

  nrg_pc_205    electricity prices for non-household (business) consumers,
                half-yearly since 2007, by consumption band -- the headline
                series, and the only one long enough to show the 2022 shock.
  nrg_pc_205_c  the same price split into its components (energy & supply,
                network costs, taxes) -- annual, 2017 onwards. This is the
                dataset the whole analysis turns on.
  nrg_pc_203    gas prices for non-household consumers, for the second
                commodity an energy retailer sells.
  nrg_pc_205    also pulled in PPS (purchasing power standard) so the
                comparison can be sanity-checked against price levels.

Countries: Czechia and its five neighbours and direct competitors for
industrial investment, plus the EU average as a reference line.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import eurostat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# Czechia, its four land neighbours, Hungary (same V4 industrial basket),
# and the EU aggregate as the reference line.
COUNTRIES = ["EU27_2020", "CZ", "DE", "AT", "PL", "SK", "HU"]

# Band ID (2 000 - 19 999 MWh/year) is the core mid-size industrial customer:
# a medium factory, a large logistics site, a hospital. Big enough to negotiate,
# small enough to be numerous -- the segment a B2B sales team lives on.
FOCUS_BAND = "MWH2000-19999"

ELECTRICITY_BANDS = [
    "MWH_LT20", "MWH20-499", "MWH500-1999", "MWH2000-19999",
    "MWH20000-69999", "MWH70000-149999", "MWH_GE150000",
]
GAS_BANDS = ["GJ_LT1000", "GJ1000-9999", "GJ10000-99999", "GJ100000-999999", "GJ_GE1000000"]

DATASETS = {
    # Excluding VAT: VAT is recoverable for a business, so the VAT-inclusive
    # series overstates what a company actually pays. This single choice changes
    # the country ranking, which is why it is stated here and in the report.
    "nrg_pc_205": {
        "geo": COUNTRIES, "currency": "EUR", "tax": "X_VAT",
        "nrg_cons": ELECTRICITY_BANDS,
    },
    "nrg_pc_205_c": {
        "geo": COUNTRIES, "currency": "EUR", "nrg_cons": FOCUS_BAND,
    },
    # Gas is published in both kWh and gigajoules. Without pinning the unit every
    # country/period appears twice, in two different magnitudes -- and a mean over
    # that mixture is a meaningless number that still looks plausible.
    "nrg_pc_203": {
        "geo": COUNTRIES, "currency": "EUR", "tax": "X_VAT",
        "nrg_cons": GAS_BANDS, "unit": "KWH",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="ignore the cache and re-download")
    args = parser.parse_args()

    for dataset, params in DATASETS.items():
        payload = eurostat.fetch(dataset, params, RAW, refresh=args.refresh)
        frame = eurostat.to_frame(payload)
        source = "cache" if not args.refresh else "Eurostat"
        print(f"{dataset:<14} {len(frame):>6,} observations  "
              f"(updated {payload.get('updated', '?')[:10]}, from {source})")
        print(f"               {payload.get('label', '')}")


if __name__ == "__main__":
    main()
