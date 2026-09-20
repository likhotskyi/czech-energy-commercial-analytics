"""
The three public sources this analysis joins, and the cache that makes it
reproducible offline.

  PVGIS     European Commission, Joint Research Centre. Hourly PV output for any
            point in Europe, from the SARAH3 satellite irradiance database.
            Free, no key, and the reference tool used across the European solar
            industry.
  energy-charts.info  Fraunhofer ISE, CC BY 4.0. Czech day-ahead auction prices,
            which are what an exported kilowatt-hour earns.
  Eurostat  Retail electricity price for business consumers, split into energy,
            network and taxes -- which is what a self-consumed kilowatt-hour
            avoids.

The whole economic argument of this project is the gap between those last two
numbers, so both have to come from somewhere citable rather than from a rule of
thumb.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "solar-self-consumption/1.0 (portfolio project; contact via GitHub)"

PVGIS = "https://re.jrc.ec.europa.eu/api/v5_3"
ENERGY_CHARTS = "https://api.energy-charts.info/price"
EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data")


def _get(url: str, retries: int = 3, timeout: int = 180) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Request failed: {url}\n{last}")


def cached(path: Path, url: str, refresh: bool = False) -> dict:
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    payload = _get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


# --------------------------------------------------------------------- PVGIS
# Panels lying close to a roof run hotter than a free-standing array and lose about
# 3.5% over the year. `mountingplace=building` tells PVGIS to model that. 35 degrees
# facing due south is the usual optimum for this latitude.
PV_DEFAULTS = {
    "peakpower": 1,          # 1 kWp, so every result scales linearly
    "loss": 14,              # system losses (%), the PVGIS default
    "angle": 35,
    "aspect": 0,             # 0 = due south in the PVGIS convention
    "mountingplace": "building",
    "outputformat": "json",
}


def pv_hourly_url(lat: float, lon: float, year: int) -> str:
    params = {**PV_DEFAULTS, "lat": lat, "lon": lon,
              "startyear": year, "endyear": year, "pvcalculation": 1}
    return f"{PVGIS}/seriescalc?{urllib.parse.urlencode(params)}"


def pv_annual_url(lat: float, lon: float) -> str:
    """Long-run average yield and its year-to-year standard deviation."""
    params = {**PV_DEFAULTS, "lat": lat, "lon": lon}
    return f"{PVGIS}/PVcalc?{urllib.parse.urlencode(params)}"


# ------------------------------------------------------------- energy-charts
def price_url(year: int, zone: str = "CZ") -> str:
    return f"{ENERGY_CHARTS}?bzn={zone}&start={year}-01-01&end={year}-12-31"


# ----------------------------------------------------------------- Eurostat
def retail_components_url(geo: str = "CZ", band: str = "MWH2000-19999") -> str:
    params = [("format", "JSON"), ("lang", "en"), ("geo", geo),
              ("nrg_cons", band), ("currency", "EUR")]
    return f"{EUROSTAT}/nrg_pc_205_c?{urllib.parse.urlencode(params)}"
