# Re-checking the numbers

Notes from a pass made on 15 September 2026, after the three reports were
finished. The idea was to go back to each API, pull the headline figures again
without looking at the stored results, and see whether they matched.

Five checks. Three matched straight away. Two did not, and both turned out to be
my own fault in the re-check rather than a problem with the reports — which is
the more useful outcome, because it forced me to work out exactly which
parameter was doing the damage.

## Eurostat prices

`nrg_pc_205`, band `MWH2000-19999`, unit `KWH`, currency `EUR`, tax basis
`X_VAT`, period `2025-S2`.

| Country | Live | Stored |
|---|---|---|
| Czechia | 0.1636 | 0.1636 |
| EU-27 | 0.1596 | 0.1596 |
| Poland | 0.1735 | 0.1735 |
| Austria | 0.1799 | 0.1799 |
| Slovakia | 0.1839 | 0.1839 |
| Hungary | 0.1876 | 0.1876 |
| Germany | 0.1922 | 0.1922 |

Gap to the EU average +2.51%, gap to Germany −14.88%, rank 1 of 6. All as
reported.

The first attempt came back with 0.1456 for Czechia, 11% out. It had queried
`tax=X_TAX`, which strips every tax and levy. The right basis for a business
customer is `X_VAT`: VAT is recoverable, the electricity tax and the renewable
levy are not. Same dataset, same band, same period — a different number because
of one parameter, and the wrong one looks perfectly reasonable on its own.

## Eurostat components

`nrg_pc_205_c`, Czechia, 2025, same band.

| | Live | Stored |
|---|---|---|
| Energy and supply | 0.1102 | 0.1102 |
| Network costs | 0.0385 | 0.0385 |
| Taxes and levies excl. VAT | 0.0179 | 0.0179 |
| Total | 0.1666 | 0.1666 |
| Commodity share | 66.1% | 66.1% |

The tax line is derived as `TAX_FEE_LEV_CHRG − VAT` = 0.0529 − 0.0350 = 0.0179,
because the published tax line includes VAT. Taking it at face value overstates
the industrial price by 21.2% and drops the commodity share to about 55%.

Worth checking a second way: `TAX_RNW` (0.0166) + `TAX_ENV` (0.0012) + `OTH`
(0.0001) also comes to 0.0179. The subtraction and the itemised breakdown agree,
which is better evidence than either on its own.

## PVGIS yield

`PVcalc` v5.3, SARAH3, 1 kWp, 35° tilt, due south, 14% system losses,
`mountingplace=building`.

| Plzeň | Live | Stored |
|---|---|---|
| Yield, kWh/kWp | 1030.84 | 1030.8 |
| Year-to-year SD | 54.36 | 54.4 |
| Irradiation, kWh/m² | 1342.43 | 1342.4 |

This one failed first too, returning 1068.09. The default `mountingplace` is
`free`; a roof-mounted array runs hotter and yields about 3.5% less. The
projects model rooftop systems, so `building` is the right setting. Irradiation
matched on both runs, which is what narrowed it down — the sun had not changed,
so the difference had to be in the module model.

## Wholesale prices

CZ day-ahead, duration-weighted over the calendar year.

| Year | Periods | Live | Stored | Negative periods |
|---|---:|---:|---:|---:|
| 2021 | 8 761 | 100.66 | 100.66 | 33 |
| 2022 | 8 761 | 247.41 | 247.43 | 8 |
| 2023 | 8 761 | 100.77 | 100.79 | 134 |
| 2024 | 8 785 | 85.10 | 85.11 | 315 |
| 2025 | 15 388 | 96.83 | 96.83 | 348 |

Differences of two hundredths of a euro come from how the final interval of the
year is handled.

2025 has 15 388 periods because the market time unit changed from 60 to 15
minutes on 1 October 2025. The duration weights sum to 8 760.2 hours, which is a
full calendar year — that is the check that the weighting is actually applied.
An unweighted mean over the same year gives 100.20 and overstates the baseload
by 3.5%, because the fourth quarter contributes four times as many rows as the
first.

## Capture rate, rebuilt from scratch

Not a re-fetch but a re-computation: PVGIS hourly output for Plzeň in 2023
reduced to a month × hour shape, each year's prices reduced the same way, then
an output-weighted average price divided by that year's baseload.

| Year | Recomputed | Stored |
|---|---|---|
| 2021 | 0.8850 | 0.8857 |
| 2024 | 0.6633 | 0.6645 |
| 2025 | 0.617 | 0.619 |

The residual difference is the month-hour bucketing. 2025 first came out at
0.5965, because the recomputation used an unweighted baseload of 100.20 instead
of the duration-weighted 96.83 — the same 15-minute trap as above, arrived at
from a different direction.

The 2023 hourly series for Plzeň sums to 1031.1 kWh/kWp against a long-run
average of 1030.84, so 2023 is close to a typical year at that site and is a
reasonable shape to use for the other years.
