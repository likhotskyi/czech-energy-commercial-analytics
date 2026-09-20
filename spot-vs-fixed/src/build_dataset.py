"""
Step 2: turn the raw price downloads into one comparable series.

Two things have to be right here, and both are the sort of thing that produces a
plausible-looking wrong answer rather than an error.

**Local time.** The API timestamps observations in UTC. Every question in this
project is about *when a factory runs* — 06:00 to 14:00, nights, weekends — and a
factory runs on Czech local time. Reading UTC as local shifts the whole analysis
by one hour in winter and two in summer, which is enough to move a lunchtime price
trough into the wrong shift. Conversion uses the Europe/Prague zone, so the
daylight-saving transitions are handled by the zone database rather than by an
assumed constant offset.

**Unequal observation lengths.** The Czech day-ahead market moved from hourly to
15-minute settlement periods on 1 October 2025 (the EU-wide switch to a 15-minute
market time unit). From that date each row covers a quarter of an hour, not an
hour. A plain average over the raw rows therefore weights an October quarter-hour
the same as a January hour — four times too much.

So every observation carries an explicit `duration_h`, and every average in this
project is duration-weighted. The size of the error is reported at the end of this
script rather than asserted.

    python src/build_dataset.py

Output: data/clean/prices.csv, data/clean/coverage.csv
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

PRAGUE = ZoneInfo("Europe/Prague")
ZONE = "CZ"


def load_year(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    seconds = payload["unix_seconds"]
    prices = payload["price"]

    frame = pd.DataFrame({"unix_seconds": seconds, "price_eur_mwh": prices})
    frame["licence"] = payload.get("license_info", "")

    # Duration of each settlement period = gap to the next observation. The final
    # observation has no successor, so it inherits the most common gap in the file.
    gaps = frame["unix_seconds"].diff().shift(-1)
    modal_gap = Counter(gaps.dropna().astype(int)).most_common(1)[0][0]
    gaps = gaps.fillna(modal_gap).astype(int)

    # A gap wider than the settlement period is missing data, not a long period.
    # Letting it stand as a duration would silently stretch the last price before
    # the gap across the hole and make the coverage check pass every time.
    known = {900, 1800, 3600}
    frame["duration_s"] = gaps.where(gaps.isin(known), modal_gap).astype(int)
    frame["gap_after_s"] = (gaps - frame["duration_s"]).clip(lower=0)
    return frame


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)

    files = sorted(RAW.glob(f"day_ahead_{ZONE}_*.json"))
    if not files:
        raise SystemExit("No raw files. Run src/fetch_prices.py first.")

    frame = pd.concat([load_year(p) for p in files], ignore_index=True)
    frame = frame.sort_values("unix_seconds").reset_index(drop=True)

    # Overlapping downloads would double-count; the year files should not overlap,
    # but this is cheap and the failure it prevents is silent.
    duplicates = int(frame["unix_seconds"].duplicated().sum())
    if duplicates:
        raise RuntimeError(f"{duplicates} duplicated timestamps across the year files.")

    frame["ts_utc"] = [datetime.fromtimestamp(s, tz=timezone.utc)
                       for s in frame["unix_seconds"]]
    frame["ts_local"] = [t.astimezone(PRAGUE) for t in frame["ts_utc"]]

    frame["duration_h"] = frame["duration_s"] / 3600
    frame["year"] = [t.year for t in frame["ts_local"]]
    frame["month"] = [t.month for t in frame["ts_local"]]
    frame["date_local"] = [t.date().isoformat() for t in frame["ts_local"]]
    frame["hour_local"] = [t.hour for t in frame["ts_local"]]
    frame["weekday"] = [t.weekday() for t in frame["ts_local"]]      # Monday = 0
    frame["is_weekend"] = frame["weekday"] >= 5
    frame["negative"] = frame["price_eur_mwh"] < 0

    missing = int(frame["price_eur_mwh"].isna().sum())
    if missing:
        raise RuntimeError(f"{missing} settlement periods have no price. "
                           f"Decide how to treat them before averaging.")

    # ------------------------------------------------------- coverage check
    # Hours actually delivered against hours the calendar says should exist. A gap
    # means a missing day; a surplus means double-counting. Either invalidates a
    # yearly average, and neither shows up in a chart.
    # The benchmark is the calendar, not the data: how many hours does the year
    # actually have in Europe/Prague, leap days and daylight-saving included? That
    # is an independent number the download cannot influence.
    rows = []
    last_local_overall = frame["ts_local"].max()
    for year, group in frame.groupby("year"):
        delivered = float(group["duration_h"].sum())
        year_start = datetime(year, 1, 1, tzinfo=PRAGUE)
        year_end = datetime(year + 1, 1, 1, tzinfo=PRAGUE)
        calendar_hours = (year_end - year_start).total_seconds() / 3600

        partial = last_local_overall.year == year
        if partial:
            covered_to = group["ts_local"].max() + timedelta(
                seconds=int(group["duration_s"].iloc[-1]))
            expected = (covered_to - year_start).total_seconds() / 3600
        else:
            expected = calendar_hours

        resolutions = sorted(set(group["duration_s"]))
        rows.append({
            "year": year,
            "observations": len(group),
            "hours_delivered": round(delivered, 2),
            "hours_expected": round(expected, 2),
            "calendar_hours_in_year": round(calendar_hours, 2),
            "gap_hours": round(expected - delivered, 2),
            "gaps_in_series_hours": round(float(group["gap_after_s"].sum()) / 3600, 2),
            "resolutions_minutes": ", ".join(str(r // 60) for r in resolutions),
            "status": "partial year" if partial else "complete year",
        })
    coverage = pd.DataFrame(rows)

    worst_gap = coverage["gap_hours"].abs().max()
    if worst_gap > 3:
        raise RuntimeError(
            f"A year is missing {worst_gap:.1f} hours of prices. Yearly averages "
            f"would be computed over an incomplete year — fix the download first.")

    columns = ["ts_utc", "ts_local", "year", "month", "date_local", "hour_local",
               "weekday", "is_weekend", "duration_h", "price_eur_mwh", "negative"]
    out = frame[columns].copy()
    out["ts_utc"] = out["ts_utc"].map(lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    out["ts_local"] = out["ts_local"].map(lambda t: t.strftime("%Y-%m-%d %H:%M:%S%z"))
    out.to_csv(CLEAN / "prices.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(CLEAN / "coverage.csv", index=False, encoding="utf-8-sig")

    # ------------------------------------------------------ report, not assert
    print(f"{len(frame):,} settlement periods, "
          f"{frame['ts_local'].min():%Y-%m-%d} to {frame['ts_local'].max():%Y-%m-%d} "
          f"(Europe/Prague)\n")
    print(coverage.to_string(index=False))

    print("\nWhat duration weighting changes:\n")
    print(f"{'year':<6}{'plain mean':>12}{'time-weighted':>15}{'difference':>12}")
    for year, group in frame.groupby("year"):
        plain = group["price_eur_mwh"].mean()
        weighted = ((group["price_eur_mwh"] * group["duration_h"]).sum()
                    / group["duration_h"].sum())
        print(f"{year:<6}{plain:>12.2f}{weighted:>15.2f}"
              f"{plain - weighted:>11.2f}%" if False else
              f"{year:<6}{plain:>12.2f}{weighted:>15.2f}"
              f"{(plain / weighted - 1) * 100:>11.2f}%")
    print("\nThe years with one resolution are unaffected, as they must be. The "
          "years\nspanning the switch are the test of whether the weighting works.")


if __name__ == "__main__":
    main()
