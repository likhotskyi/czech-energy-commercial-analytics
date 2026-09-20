"""
Step 2: turn three raw sources into aligned, analysis-ready tables.

The join is the whole point of this project, and it only works if the clocks agree.

**PVGIS timestamps are UTC.** Nothing in the response says so, so it was verified
rather than assumed: for Brno, at longitude 16.606 E, solar noon falls at
12:00 - 16.606/15 = 10:53 UTC. The observed June output peaks in the hour labelled
10, and the December peak one hour later, exactly as the equation of time predicts.
That is consistent with UTC and inconsistent with local time, which would put the
June peak at 12 or 13. Both PV and prices are therefore converted to Europe/Prague
before anything is joined.

Reading the PV series as local time would shift generation two hours earlier in
summer against the load, and self-consumption is precisely a question of overlap --
the error would change every result while leaving every chart looking normal.

    python src/build_dataset.py

Outputs
    data/clean/pv_hourly.csv     kW per kWp installed, by location and local hour
    data/clean/prices_2023.csv   day-ahead price for the analysis year
    data/clean/price_shape.csv   average price by year, month and hour
    data/clean/retail.csv        retail price split into its components
    data/clean/pv_annual.csv     long-run yield and its year-to-year variation
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import fetch_data

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
PRAGUE = ZoneInfo("Europe/Prague")

ANALYSIS_YEAR = fetch_data.ANALYSIS_YEAR


def load_pv_hourly() -> pd.DataFrame:
    frames = []
    for location in fetch_data.LOCATIONS:
        payload = json.loads(
            (RAW / f"pv_hourly_{location['key']}_{ANALYSIS_YEAR}.json")
            .read_text(encoding="utf-8"))
        rows = payload["outputs"]["hourly"]

        # "20230616:1610" -> 2023-06-16 16:10 UTC. The :10 is PVGIS's mid-interval
        # convention for satellite data; the interval is the hour it starts.
        stamps = [datetime.strptime(r["time"][:11], "%Y%m%d:%H")
                  .replace(tzinfo=timezone.utc) for r in rows]
        frame = pd.DataFrame({
            "ts_utc": stamps,
            "watt_per_kwp": [r["P"] for r in rows],
            "irradiance_w_m2": [r["G(i)"] for r in rows],
            "module_temp_c": [r["T2m"] for r in rows],
        })
        frame["location"] = location["name"]
        frame["location_key"] = location["key"]
        frame["region"] = location["region"]
        frames.append(frame)

    pv = pd.concat(frames, ignore_index=True)
    pv["ts_local"] = [t.astimezone(PRAGUE) for t in pv["ts_utc"]]
    pv["month"] = [t.month for t in pv["ts_local"]]
    pv["hour"] = [t.hour for t in pv["ts_local"]]
    pv["date_local"] = [t.date().isoformat() for t in pv["ts_local"]]
    pv["weekday"] = [t.weekday() for t in pv["ts_local"]]
    pv["is_weekend"] = pv["weekday"] >= 5
    # 1 kWp system, output in W -> kW, which for an hourly period is also kWh.
    pv["kw_per_kwp"] = pv["watt_per_kwp"] / 1000
    pv["ts_utc_hour"] = pv["ts_utc"].map(
        lambda t: t.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00:00Z"))
    return pv


def load_prices(year: int, by: str = "local") -> pd.DataFrame:
    """
    `by="local"` selects the calendar year as a Czech reader means it, which is
    what the month-and-hour price shapes need. `by="utc"` selects the same span the
    PV series covers, so the two join hour for hour with nothing left over -- the
    difference is one hour at each end of the year, and it is exactly the hour that
    would otherwise come through as a missing price.
    """
    payload = json.loads((RAW / f"day_ahead_CZ_{year}.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame({"unix_seconds": payload["unix_seconds"],
                          "price_eur_mwh": payload["price"]})
    gaps = frame["unix_seconds"].diff().shift(-1)
    modal = Counter(gaps.dropna().astype(int)).most_common(1)[0][0]
    gaps = gaps.fillna(modal).astype(int)
    frame["duration_s"] = gaps.where(gaps.isin({900, 1800, 3600}), modal).astype(int)
    frame["duration_h"] = frame["duration_s"] / 3600

    frame["ts_local"] = [datetime.fromtimestamp(s, tz=timezone.utc).astimezone(PRAGUE)
                         for s in frame["unix_seconds"]]
    frame["year"] = [t.year for t in frame["ts_local"]]
    frame["month"] = [t.month for t in frame["ts_local"]]
    frame["hour"] = [t.hour for t in frame["ts_local"]]
    frame["date_local"] = [t.date().isoformat() for t in frame["ts_local"]]
    frame["weekday"] = [t.weekday() for t in frame["ts_local"]]
    frame["is_weekend"] = frame["weekday"] >= 5
    if by == "utc":
        utc_year = [datetime.fromtimestamp(v, tz=timezone.utc).year
                    for v in frame["unix_seconds"]]
        frame = frame.assign(utc_year=utc_year)
        return frame[frame["utc_year"] == ANALYSIS_YEAR]
    return frame[frame["year"] == year]


def hourly_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse settlement periods to hourly means, keyed on the UTC hour.

    The key matters. Keying on (local date, local hour) looks natural and loses a
    row every year: on the October clock change 02:00 local happens twice, and the
    two different hours collapse into one. Joining on UTC is exact, and the local
    labels ride along for the load profiles, which genuinely do care about local
    time.
    """
    frame = frame.copy()
    frame["ts_utc_hour"] = [
        datetime.fromtimestamp(s, tz=timezone.utc).replace(minute=0, second=0)
        for s in frame["unix_seconds"]]
    grouped = frame.groupby("ts_utc_hour")
    out = grouped.apply(lambda g: pd.Series({
        "price_eur_mwh": float(np.average(g["price_eur_mwh"], weights=g["duration_h"])),
        "hours": float(g["duration_h"].sum()),
        "date_local": g["date_local"].iloc[0],
        "hour": int(g["hour"].iloc[0]),
        "month": int(g["month"].iloc[0]),
        "is_weekend": bool(g["is_weekend"].iloc[0]),
    }), include_groups=False).reset_index()
    out["ts_utc_hour"] = out["ts_utc_hour"].map(
        lambda t: t.strftime("%Y-%m-%dT%H:00:00Z"))
    return out


def load_retail() -> pd.DataFrame:
    payload = json.loads((RAW / "retail_components_CZ.json").read_text(encoding="utf-8"))
    dims = payload["id"]
    sizes = payload["size"]
    decoders = []
    for dim in dims:
        index = payload["dimension"][dim]["category"]["index"]
        ordered = (sorted(index.items(), key=lambda kv: kv[1])
                   if isinstance(index, dict) else [(c, i) for i, c in enumerate(index)])
        decoders.append([code for code, _ in ordered])
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    rows = []
    for flat, value in payload["value"].items():
        remainder = int(flat)
        row = {}
        for dim, stride, codes in zip(dims, strides, decoders):
            position, remainder = divmod(remainder, stride)
            row[dim] = codes[position]
        row["value"] = value
        rows.append(row)

    frame = pd.DataFrame(rows)
    wide = frame.pivot_table(index="time", columns="nrg_prc", values="value")

    # Eurostat's tax line is a total that already contains VAT, while the price a
    # business actually pays excludes VAT because it is recoverable. Subtracting it
    # is what makes these components add up to the published retail price.
    wide["taxes_excl_vat"] = wide["TAX_FEE_LEV_CHRG"] - wide["VAT"]
    wide["retail_excl_vat"] = wide["NRG_SUP"] + wide["NETC"] + wide["taxes_excl_vat"]
    out = wide.reset_index().rename(columns={"NRG_SUP": "energy_supply",
                                             "NETC": "network", "time": "year"})
    return out[["year", "energy_supply", "network", "taxes_excl_vat",
                "retail_excl_vat"]].sort_values("year")


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)

    pv = load_pv_hourly()
    columns = ["location", "location_key", "region", "ts_utc_hour", "date_local",
               "month", "hour", "weekday", "is_weekend", "kw_per_kwp",
               "irradiance_w_m2", "module_temp_c"]
    pv[columns].to_csv(CLEAN / "pv_hourly.csv", index=False, encoding="utf-8-sig")

    # The price file for a year is requested in local dates, so it runs from
    # 23:00 UTC on 31 December of the previous year to 22:00 UTC on 31 December.
    # The last UTC hour of the analysis year therefore lives in the *next* year's
    # file. Concatenating the neighbours before filtering is what makes the UTC year
    # complete; without it the join silently loses its final hour.
    neighbours = [y for y in (ANALYSIS_YEAR, ANALYSIS_YEAR + 1)
                  if (RAW / f"day_ahead_CZ_{y}.json").exists()]
    combined = pd.concat([load_prices(y, by="utc") for y in neighbours],
                         ignore_index=True)
    combined = combined.drop_duplicates(subset="unix_seconds")
    prices_analysis = hourly_prices(combined)
    prices_analysis.to_csv(CLEAN / "prices_2023.csv", index=False, encoding="utf-8-sig")

    shapes = []
    for year in fetch_data.PRICE_YEARS:
        frame = load_prices(year)
        block = frame.groupby(["month", "hour"]).apply(
            lambda g: float(np.average(g["price_eur_mwh"], weights=g["duration_h"])),
            include_groups=False).rename("price_eur_mwh").reset_index()
        block["year"] = year
        baseload = float(np.average(frame["price_eur_mwh"], weights=frame["duration_h"]))
        block["year_baseload"] = round(baseload, 3)
        shapes.append(block)
    shape = pd.concat(shapes, ignore_index=True)
    shape.to_csv(CLEAN / "price_shape.csv", index=False, encoding="utf-8-sig")

    retail = load_retail()
    retail.to_csv(CLEAN / "retail.csv", index=False, encoding="utf-8-sig")

    annual_rows = []
    for location in fetch_data.LOCATIONS:
        payload = json.loads((RAW / f"pv_annual_{location['key']}.json")
                             .read_text(encoding="utf-8"))
        totals = payload["outputs"]["totals"]["fixed"]
        annual_rows.append({
            "location": location["name"],
            "region": location["region"],
            "latitude": location["lat"],
            "longitude": location["lon"],
            "yield_kwh_per_kwp": round(totals["E_y"], 1),
            "st_dev_kwh": round(totals["SD_y"], 1),
            "variability_pct": round(totals["SD_y"] / totals["E_y"] * 100, 1),
            "irradiation_kwh_m2": round(totals["H(i)_y"], 1),
        })
    annual = pd.DataFrame(annual_rows).sort_values("yield_kwh_per_kwp", ascending=False)
    annual.to_csv(CLEAN / "pv_annual.csv", index=False, encoding="utf-8-sig")

    # ------------------------------------------------------------------ checks
    problems = []
    for location, group in pv.groupby("location"):
        hours = len(group)
        if hours != 8760:
            problems.append(f"{location}: {hours} hours, expected 8760")
        night = group[(group["hour"] < 3) | (group["hour"] > 22)]
        if float(night["kw_per_kwp"].max()) > 0.001:
            problems.append(f"{location}: non-zero output in the middle of the night "
                            f"— the timezone conversion is wrong")
        summer_peak = (group[group["month"] == 6].groupby("hour")["kw_per_kwp"]
                       .mean().idxmax())
        if not 11 <= summer_peak <= 14:
            problems.append(f"{location}: June output peaks at {summer_peak}:00 local, "
                            f"which is not around solar noon")
    if problems:
        raise RuntimeError("Alignment checks failed:\n  " + "\n  ".join(problems))

    if len(prices_analysis) != 8760:
        raise RuntimeError(f"{len(prices_analysis)} price hours for {ANALYSIS_YEAR}")
    pv_hours = set(pv["ts_utc_hour"])
    price_hours = set(prices_analysis["ts_utc_hour"])
    if pv_hours != price_hours:
        raise RuntimeError(
            f"PV and price hours do not match: {len(pv_hours - price_hours)} PV hours "
            f"have no price, {len(price_hours - pv_hours)} prices have no PV hour. "
            f"Every joined hour must exist in both, or the annual totals are wrong.")

    print(f"pv_hourly.csv     {len(pv):,} rows "
          f"({pv['location'].nunique()} locations x 8,760 hours)")
    print(f"prices_2023.csv   {len(prices_analysis):,} hours")
    print(f"price_shape.csv   {len(shape):,} rows "
          f"({shape['year'].nunique()} years x 12 months x 24 hours)")
    print(f"retail.csv        {len(retail)} years, latest "
          f"{int(retail['year'].max())}")
    print(f"\nAlignment checks passed: no night-time generation, June output peaks "
          f"at midday local time,\nand every location has a complete year.\n")
    print(annual.to_string(index=False))


if __name__ == "__main__":
    main()
