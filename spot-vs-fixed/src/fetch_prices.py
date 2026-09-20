"""
Step 1: download Czech day-ahead electricity prices and cache them.

Source: energy-charts.info, run by Fraunhofer ISE, licence CC BY 4.0. It
republishes the day-ahead auction results for each European bidding zone; `bzn=CZ`
is the Czech zone. Prices are EUR/MWh, timestamped in **UTC**.

    python src/fetch_prices.py [--refresh]

Why day-ahead and not a retail price: a spot-indexed contract settles against this
auction. It is the actual reference a customer on a spot product pays, hour by
hour, which is what makes the comparison in this project meaningful rather than
illustrative.

One year per file, so a partial year can be refreshed without re-downloading the
history, and so the cache stays readable.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

BASE = "https://api.energy-charts.info/price"
ZONE = "CZ"
USER_AGENT = "spot-vs-fixed/1.0 (portfolio project; contact via GitHub)"

# Five complete calendar years plus the current year to date. The history has to
# start before 2022: without a pre-crisis year there is no way to tell a
# structural change in the price shape from the after-effects of the gas shock.
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
PARTIAL_YEAR_END = "2026-08-31"       # last complete month at the time of writing


def fetch_year(year: int, refresh: bool) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"day_ahead_{ZONE}_{year}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))

    start = f"{year}-01-01"
    end = PARTIAL_YEAR_END if year == YEARS[-1] else f"{year}-12-31"
    url = f"{BASE}?bzn={ZONE}&start={start}&end={end}"

    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(f"Download failed for {year}: {exc}") from exc
            time.sleep(2 * (attempt + 1))

    if "price" not in payload or not payload["price"]:
        raise RuntimeError(f"No price data returned for {year}")
    if len(payload["price"]) != len(payload["unix_seconds"]):
        raise RuntimeError(f"{year}: timestamps and prices differ in length "
                           f"({len(payload['unix_seconds'])} vs {len(payload['price'])})")

    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    print(f"{'year':<6}{'points':>8}{'missing':>9}{'min':>9}{'max':>9}{'mean':>9}   licence")
    for year in YEARS:
        payload = fetch_year(year, args.refresh)
        prices = payload["price"]
        present = [p for p in prices if p is not None]
        missing = len(prices) - len(present)
        licence = payload.get("license_info", "")[:28]
        print(f"{year:<6}{len(prices):>8,}{missing:>9}"
              f"{min(present):>9.1f}{max(present):>9.1f}"
              f"{sum(present) / len(present):>9.1f}   {licence}")

    print("\nPrices are EUR/MWh, timestamped in UTC. The 'mean' above is a plain "
          "average of the\nraw points and is NOT the baseload price — see "
          "src/build_dataset.py for why.")


if __name__ == "__main__":
    main()
