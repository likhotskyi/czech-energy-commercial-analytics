# Method

Every choice below could have gone another way. Each is written down with its reason,
because a number you cannot explain is a number you cannot defend in a meeting.

---

## 1. The data

Day-ahead auction prices for the Czech bidding zone, from
[energy-charts.info](https://energy-charts.info) (Fraunhofer ISE), licence CC BY 4.0.
The raw API responses are cached in `data/raw/`, one file per year.

| Year | Settlement periods | Resolution | Status |
|---|---:|---|---|
| 2021 | 8 760 | hourly | complete |
| 2022 | 8 760 | hourly | complete |
| 2023 | 8 760 | hourly | complete |
| 2024 | 8 784 | hourly | complete (leap year) |
| 2025 | 15 387 | hourly, then 15-minute from 1 October | complete |
| 2026 | 23 324 | 15-minute | January–August only |

**Why the day-ahead auction and not a retail price.** A spot-indexed contract settles
against this auction. It is the actual reference a customer on a spot product pays,
period by period. A retail price index would be a proxy for it.

**Why 2021 is the first year.** Without a pre-crisis year there is no way to separate
a structural change in the price *shape* from the after-effects of the 2022 gas shock.
2021 is the last normal year, and it is the comparison that makes the finding readable.

## 2. The choices that shape the result

### Local time, not UTC

The API timestamps in UTC. Every question in this project is about *when a factory
runs*: 06:00 to 14:00, nights, weekends. A factory runs on Czech local time.

Reading UTC as local shifts everything by one hour in winter and two in summer —
enough to move the midday price trough into the wrong shift and to put an hour of the
evening peak inside the day shift. Conversion uses the `Europe/Prague` zone, so the
daylight-saving transitions come from the zone database rather than an assumed
constant offset.

### Duration weighting

The Czech market moved from hourly to 15-minute settlement periods on 1 October 2025,
with the EU-wide switch to a 15-minute market time unit. From that date each
observation covers a quarter of an hour.

A plain average over the raw rows therefore weights an October quarter-hour the same
as a January hour — four times too much. Every average in this project is weighted by
period length instead.

`build_dataset.py` prints the difference rather than asserting it:

| Year | Plain mean | Duration-weighted | Difference |
|---|---:|---:|---:|
| 2021 | 100.66 | 100.66 | 0.00% |
| 2022 | 247.43 | 247.43 | 0.00% |
| 2023 | 100.79 | 100.79 | 0.00% |
| 2024 | 85.11 | 85.11 | 0.00% |
| **2025** | **100.19** | **96.83** | **3.48%** |
| 2026 | 110.69 | 110.69 | 0.00% |

Exactly zero for every single-resolution year, and non-zero only for the year that
spans the switch. That pattern is the test: a weighting that was wrong would not
produce zeros where zeros are required.

### A base load that does not go to zero

A factory running one shift still has lighting, compressed air, ventilation, IT and
standby losses overnight. Treating the off-shift as zero exaggerates every profile
effect — it is the most common way a shape analysis overstates its own conclusion.

Each profile therefore carries an explicit base load, stated in `src/profiles.py` and
carried into the workbook as editable inputs:

| Profile | Operating hours | Base load | Weekend |
|---|---|---:|---:|
| Continuous 24/7 | all | — | 100% |
| Three shifts, Mon–Fri | all weekday hours | — | 35% |
| Two shifts, Mon–Fri | 06:00–22:00 | 25% | 20% |
| Single shift, Mon–Fri | 06:00–14:00 | 20% | 15% |
| Office hours, Mon–Fri | 08:00–18:00 | 15% | 15% |
| Night-heavy, daily | 22:00–06:00 | 45% by day | 45% |

The sensitivity is reported below. With the base load switched off entirely the
office factor runs **1.19 → 0.87** instead of **1.12 → 0.92**: the same direction,
roughly twice the size. Both versions are in `findings.json`.

### Indexing the intraday chart

The price *level* moved enormously across these years — 2022 averaged 2.5 times 2024 —
so raw hourly prices cannot share an axis across years without the level drowning the
shape. Each year's hourly averages are indexed to that year's own baseload, which is
what makes the shapes comparable. The same logic applies to the seasonal factors,
which are computed against each season's own baseload so they measure shape rather
than the fact that winter power costs more.

## 3. Coverage, checked against the calendar

A missing day would not raise an error anywhere — it would just quietly shrink a
yearly average. So delivered hours are compared against an independent number: how
many hours the calendar year actually has in Europe/Prague.

The first version of this check compared the first and last observation against the
sum of the durations, which is the same quantity twice and can never fail. It was
replaced with the calendar comparison, and the gap between periods is tracked
separately so a hole in the middle of a year cannot be absorbed into the duration of
the observation before it.

Result: 8 760 hours delivered for 2021, 2022, 2023 and 2025; 8 784 for the leap year
2024; 5 831 for January–August 2026. Zero gaps.

## 4. The workbook computes its own answer

The profile factors in `output/spot_vs_fixed_czech_market.xlsx` are not values pasted
in by Python. They are `SUMPRODUCT` formulas over a price grid of year × day type ×
hour, with the load weights pulled in by `INDEX`/`MATCH` from an editable table.

This is exact rather than approximate, and it is worth knowing why: each profile's
weight depends only on the day type and the hour, so grouping the prices by
(year, day type, hour) and weighting by the hours in each cell reproduces the
settlement-period calculation term for term.

`build_excel_report.py` verifies that it does — all 36 factors against
`findings.json` — before writing the file, and raises rather than shipping a workbook
that disagrees with the report.

That check earned its place immediately. The weight columns were first written
*beside* the table rather than inside it, so `Grid[w_office]` referred to a column the
table did not declare and every factor cell in Excel returned `#NAME?` — while the
Python-side verification passed, because Python was not evaluating the formulas. It
was caught by recalculating the finished workbook in LibreOffice and comparing the
computed cells against `findings.json`, which is now part of the build routine.

The lookup also avoids a two-column `MATCH`, which requires an array formula that
older Excel only accepts with Ctrl+Shift+Enter. A single join key column is one extra
column and works everywhere; a workbook that breaks silently on someone else's machine
is worse than one that is slightly less elegant.

## 5. How to verify any number by hand

Nothing here requires trust.

**A single price**, straight from the source:

```bash
curl -s "https://api.energy-charts.info/price?bzn=CZ&start=2026-06-15&end=2026-06-16" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['unit'], d['price'][:8])"
```

**The same value from the cached copy** this report was built from:

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('data/clean/prices.csv', encoding='utf-8-sig')
print(df[df.ts_local.str.startswith('2026-06-15')].head(8)[['ts_local','price_eur_mwh']])"
```

**A profile factor**, recomputed from scratch in four lines:

```bash
python3 -c "
import pandas as pd, numpy as np
df = pd.read_csv('data/clean/prices.csv', encoding='utf-8-sig')
g = df[df.year == 2026]
mask = (~g.is_weekend) & g.hour_local.between(8, 17)
w = np.where(mask, 1.0, 0.15) * g.duration_h
print(np.average(g.price_eur_mwh, weights=w) / np.average(g.price_eur_mwh, weights=g.duration_h))"
```

That prints the office-hours factor for 2026. It should agree with the table in the
README, the workbook and the deck, because all three read the same `findings.json`.

**Or open the workbook** and change a load weight. The factors are formulas; they will
move.

## 6. Limitations

- **Stylised profiles, not metered customer data.** Real sites have shutdowns,
  seasonality and production peaks.
- **Shape only.** Forward prices, risk premia and balancing costs are not public and
  are not modelled, so this does not decide spot against fixed on its own.
- **History rather than forecast.** Four consistent years are evidence about direction. Not a
  guarantee about the term of a contract signed today.
- **One bidding zone.** Cross-border effects are visible only through their effect on
  Czech prices.
- **2026 is partial** (January–August) and labelled as such wherever it appears.
- **Negative prices are reported, not modelled.** Whether a customer can actually
  move load into them depends on its process, which no public dataset knows.
