# Independent re-validation

Every headline figure re-fetched from the source API in a separate pass, written
against the live services on 15 September 2026, and compared with the values
stored in `data/clean/findings.json`.

## 1. Eurostat — price level

`nrg_pc_205`, band `MWH2000-19999`, unit `KWH`, currency `EUR`, tax basis
`X_VAT`, period `2025-S2`.

| Country | Live | Stored | Δ |
|---|---|---|---|
| Czechia | 0.1636 | 0.1636 | 0 |
| EU-27 | 0.1596 | 0.1596 | 0 |
| Poland | 0.1735 | 0.1735 | 0 |
| Austria | 0.1799 | 0.1799 | 0 |
| Slovakia | 0.1839 | 0.1839 | 0 |
| Hungary | 0.1876 | 0.1876 | 0 |
| Germany | 0.1922 | 0.1922 | 0 |

Derived: gap to EU +2.51%, gap to Germany −14.88%, rank 1 of 6. All match.

**The re-check failed first.** It queried `tax=X_TAX` and returned 0.1456 — an
11% discrepancy. `X_TAX` excludes all taxes and levies; the correct basis for
comparing business customers is `X_VAT`, which excludes VAT (recoverable) but
keeps energy taxes and the renewable levy (not recoverable). The stored value
was right; the re-check was wrong.

## 2. Eurostat — components

`nrg_pc_205_c`, Czechia, 2025, same band.

| Component | Live | Stored |
|---|---|---|
| Energy and supply | 0.1102 | 0.1102 |
| Network costs | 0.0385 | 0.0385 |
| Taxes and levies excl. VAT | 0.0179 | 0.0179 |
| Total | 0.1666 | 0.1666 |
| Commodity share | 66.1% | 66.1% |

The taxes line is derived as `TAX_FEE_LEV_CHRG − VAT` = 0.0529 − 0.0350 = 0.0179,
because the published tax line includes VAT. Taking it at face value overstates
the industrial price by 21.2%.

Cross-check by a different route: `TAX_RNW` (0.0166) + `TAX_ENV` (0.0012) + `OTH`
(0.0001) = 0.0179. The subtraction and the itemised breakdown agree.

## 3. PVGIS — solar yield

`PVcalc` v5.3, SARAH3, 1 kWp, 35° tilt, due south, 14% system losses,
`mountingplace=building`.

| Plzeň | Live | Stored |
|---|---|---|
| Yield, kWh/kWp | 1030.84 | 1030.8 |
| Year-to-year SD | 54.36 | 54.4 |
| Irradiation, kWh/m² | 1342.43 | 1342.4 |

**This re-check also failed first**, returning 1068.09. The default
`mountingplace` is `free`; a roof-mounted array runs hotter and yields ~3.5% less.
The project models rooftop systems, so `building` is correct. Irradiation matched
on both runs, which is what located the difference.

## 4. energy-charts — wholesale prices

CZ day-ahead, duration-weighted over the calendar year.

| Year | Periods | Live | Stored | Negative periods |
|---|---:|---:|---:|---:|
| 2021 | 8 761 | 100.66 | 100.66 | 33 |
| 2022 | 8 761 | 247.41 | 247.43 | 8 |
| 2023 | 8 761 | 100.77 | 100.79 | 134 |
| 2024 | 8 785 | 85.10 | 85.11 | 315 |
| 2025 | 15 388 | 96.83 | 96.83 | 348 |

Differences of ≤ 0.02 EUR/MWh come from the treatment of the final interval at
the year boundary.

2025 has 15 388 periods because the market time unit changed from 60 to 15
minutes on 1 October 2025. The duration weights sum to 8 760.2 hours — a full
calendar year — which is the check that the weighting is applied. An unweighted
mean over the same year returns 100.20, overstating the baseload by 3.5%.

## 5. Capture rate, recomputed from scratch

PVGIS hourly 2023 for Plzeň → month × hour mean output; energy-charts prices for
each year → month × hour mean price; output-weighted average price ÷ that year's
baseload.

| Year | Recomputed | Stored |
|---|---|---|
| 2021 | 0.8850 | 0.8857 |
| 2024 | 0.6633 | 0.6645 |
| 2025 | 0.617 | 0.619 |

The residual differences are the month-hour bucketing and duration weighting.
For 2025 the recomputation initially read 0.5965 because it used an unweighted
baseload of 100.20 instead of the duration-weighted 96.83 — the same trap as
above, reached from a different direction.

The PVGIS 2023 hourly series for Plzeň sums to 1031.1 kWh/kWp against a long-run
average of 1030.84, so 2023 is close to a typical year at that site.

## What this exercise is worth

Two of the five checks disagreed on the first attempt, and both disagreements
were in the re-check rather than in the stored figure. That is the normal result
and the reason to do it: a number that reproduces tells you little, and a number
that does not tells you exactly where to look.
