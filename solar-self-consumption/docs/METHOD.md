# Method

Every choice below could have gone another way. Each is written down with its reason.

---

## 1. The model

For each location, load profile and system size, hour by hour across a full year:

```
generation    = normalised PV shape x (annual consumption x system size)
load          = normalised profile shape x annual consumption
self-consumed = min(generation, load)
exported      = generation - self-consumed
saving        = self-consumed x avoided retail price
                + exported x wholesale price in that hour
```

**Why hourly and not monthly.** Netting generation against consumption over a month —
which is how a lot of quick solar arithmetic is done — lets August sunshine cancel a
February night and overstates self-consumption enormously. The question is whether
the kilowatt-hour is used *in the hour it is generated*, and nothing coarser answers it.

**Why `min()` and not a net-metering assumption.** Czech business customers do not net
annually. Surplus leaves the site and is sold; the model prices it as sold.

**Negative hours are curtailed.** Exporting into a negative price to earn negative
revenue is a modelling artefact, not a business decision — an inverter can be turned
down. The curtailed volume is reported separately rather than hidden.

## 2. Sizing: two different yields, deliberately

The hourly series is one specific year (2023, the most recent PVGIS publishes). The
kilowatt-peak a customer would actually install is sized against the **long-run
average** yield, because that is what the array will produce over twenty years.

So the model uses:

- the **2023 shape** for *when* the energy arrives, and
- the **long-run average yield** for *how much a kilowatt-peak delivers*.

This matters and it was not obvious. The first version sized on the 2023 yield while
the workbook's Locations sheet carried the long-run figure, and the two disagreed by
half a month of payback. The check that caught it is described in section 5.

## 3. What a self-consumed kilowatt-hour avoids

This is the assumption with the most leverage, and there is no single right answer:
network charges for Czech business customers are partly **capacity**-based, and a
capacity charge does not fall when consumption does.

So the model runs three scenarios and reports all three (2025 Eurostat components for
the 2 000–19 999 MWh band, excluding VAT, since VAT is recoverable for a business):

| Scenario | EUR/kWh | What it assumes |
|---|---:|---|
| Commodity only | 0.1102 | Network charges entirely capacity-based |
| **Commodity and taxes** | **0.1281** | Network capacity-based, taxes volumetric — the headline |
| Full retail | 0.1666 | The whole variable price avoided, network included |

The truth for any given customer is between the second and the third, and depends on
its tariff. Quoting one number without saying which would be the easiest way to be
wrong here by a third.

The components come from Eurostat's `nrg_pc_205_c`, where the published tax line is a
total that already contains VAT. It has to be subtracted before the components add up
to the price a business actually pays — without that, the retail price comes out
about a fifth too high, and so does every saving computed from it.

## 4. Load profiles

Six stylised profiles, each a recognisable kind of customer. Full definitions,
including the base load each keeps overnight, are in `src/profiles.py` and are carried
into the workbook's Assumptions sheet.

The base load matters: a factory running one shift still has lighting, compressed air,
ventilation and standby losses at night. Treating the off-shift as zero would
exaggerate every result. Nothing in these profiles drops below 15% of its operating
load.

## 5. The checks, and what they caught

**PVGIS timestamps are UTC — verified, not assumed.** The API response does not say
which timezone it uses. For Brno at longitude 16.606°E, solar noon falls at
12:00 − 16.606/15 = **10:53 UTC**. The observed June output peaks in the hour labelled
**10**, and the December peak one hour later, exactly as the equation of time
predicts. That is consistent with UTC and inconsistent with local time, which would
put the June peak at 12 or 13.

Reading the series as local time would shift generation two hours earlier in summer
against the load. Self-consumption is precisely a question of overlap, so the error
would change every result while leaving every chart looking normal.

The build then asserts the consequence rather than trusting the reasoning: no
generation in the middle of the night, and a June peak between 11:00 and 14:00 local,
for every location.

**The join is on the UTC hour.** Keying on (local date, local hour) looks natural and
loses a row every year: on the October clock change 02:00 local happens twice and the
two different hours collapse into one. The build compares the two sets of hours and
fails if they are not identical.

That check found a second, less obvious problem. A price file requested for a calendar
year runs from 23:00 UTC on 31 December of the *previous* year to 22:00 UTC on 31
December — so the last UTC hour of the analysis year lives in the *next* year's file.
The neighbours are concatenated before filtering, or the join quietly loses its final
hour and every annual total is short by one.

**The workbook is checked against the model.** `build_excel_report.py` recomputes the
calculator's default case independently and refuses to write the file if it disagrees
with `findings.json`. The finished workbook was then recalculated in a spreadsheet
engine and compared cell by cell — 582.07 kWp, 83.7%, 68 069 EUR, 8.55 years — because
a Python-side check cannot see whether an Excel formula actually evaluates.

## 6. How to verify any number by hand

**The yield for a location**, straight from the source:

```bash
curl -s "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=49.747&lon=13.377\
&peakpower=1&loss=14&angle=35&aspect=0&mountingplace=building&outputformat=json" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['outputs']['totals']['fixed'])"
```

That is Plzeň: `E_y` should be about 1 031 kWh/kWp with a standard deviation near 54.

**The self-consumption rate**, recomputed from the cached data in five lines:

```bash
python3 -c "
import pandas as pd, numpy as np
pv = pd.read_csv('data/clean/pv_hourly.csv', encoding='utf-8-sig')
s = pv[pv.location == 'Plzeň'].sort_values('ts_utc_hour')
w = np.where((~s.is_weekend) & s.hour.between(8, 17), 1.0, 0.15)
load = w / w.sum() * 2_000_000
gen = s.kw_per_kwp / s.kw_per_kwp.sum() * 600_000
print(np.minimum(gen, load).sum() / gen.sum())"
```

That prints the office-hours rate at a 30% system. It should match the README, the
workbook and the deck, because all three read the same `findings.json`.

**Or open the workbook** and change an input. The Calculator is formulas.

## 7. Limitations

- **Stylised profiles, not metered data.** Real sites have shutdowns, seasonality and
  production peaks.
- **Simple payback**, undiscounted, before subsidy, grant, tax treatment,
  maintenance, inverter replacement or degradation. It ranks customers; it does not
  finance a project.
- **Capex is a range**, and a real project is quoted rather than benchmarked.
- **One weather year** for the hourly shape; the resource varies about 5% year to
  year.
- **City-centre coordinates**, not a specific roof. Orientation, pitch and shading
  move the result and are site survey work.
- **No storage, no load shifting, no demand charges.** A battery or a shifted process
  changes the overlap, which is the point of the third recommendation rather than a
  gap in the model.
