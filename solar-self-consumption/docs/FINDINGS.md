# Findings

Rooftop solar on Czech business sites. 43 800 modelled hours — five locations across
a full year — joined to Czech day-ahead prices and Eurostat retail components.
Reference case: a 2 000 MWh/year site in Plzeň, the median-yield location of the five.

Every figure is generated from `data/clean/findings.json`; none is typed by hand.

---

## 1. A self-consumed kilowatt-hour is worth 3.4 times an exported one

| | EUR/kWh |
|---|---:|
| Retail price avoided by self-consumption (energy + taxes, excl. VAT) | **0.128** |
| Wholesale price earned on export, in the hours solar actually generates | **0.038** |
| Ratio | **3.4×** |

The gap is not an accident of one year. It is structural, and it has two causes that
both point the same way.

Retail price is mostly things export does not earn: energy and supply is 0.110 EUR/kWh
of the 0.167 full retail price, and taxes add another 0.018. Export earns only the
commodity, and only at the moment it is produced.

And solar produces at the worst moment. Which is the second finding.

## 2. The export half is worth less every year

A modelled estimate of the price solar earns on the Czech wholesale market, against
the flat baseload price of the same year. The generation shape is PVGIS output for
Plzeň averaged by month and hour; the prices are the actual day-ahead prices of each
year. No metered plant is involved, so read these as what a south-facing rooftop
array at that location would have earned, not as a recorded result:

| Year | Capture price | Baseload | Capture rate |
|---|---:|---:|---:|
| 2021 | 89.15 | 100.66 | **0.89** |
| 2022 | 245.57 | 247.43 | 0.99 |
| 2023 | 84.88 | 100.78 | 0.84 |
| 2024 | 56.56 | 85.11 | 0.66 |
| 2025 | 59.93 | 96.83 | **0.62** |

*EUR/MWh. Capture price = the modelled-output-weighted average price.*

On this basis solar earned 89% of the baseload price in 2021 and 62% in 2025. The mechanism is
self-inflicted: more solar on the system depresses the price in exactly the hours
solar generates. 2022 is the exception that confirms it — during the gas crisis the
whole curve rose together and the shape effect was swamped.

The commercial reading: the half of a system's output that leaves the site is worth
less with every year that passes, and the premium on self-consumption widens
accordingly. An investment case built on export revenue is building on the part of
the business that is structurally eroding.

## 3. The profile sets the size, not whether to build

Share of generation consumed on site, by load profile and system size:

| Profile | 5% | 10% | 15% | 20% | 30% | 40% | 50% | 60% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Continuous 24/7 | 100.0 | 100.0 | 100.0 | 96.4 | 80.8 | 68.1 | 58.9 | 51.9 |
| Three shifts, Mon–Fri | 100.0 | 97.6 | 93.0 | 89.4 | 77.6 | 66.2 | 57.4 | 50.7 |
| Two shifts, Mon–Fri | 100.0 | 94.9 | 90.1 | 86.9 | 82.4 | 74.1 | 65.9 | 59.0 |
| Single shift, Mon–Fri | 100.0 | 96.4 | 88.1 | 81.4 | 72.8 | 67.5 | 62.8 | 57.4 |
| **Office hours, Mon–Fri** | 100.0 | 96.1 | 91.2 | 88.0 | 83.7 | 81.0 | 76.6 | **70.7** |
| **Night-heavy, daily** | 100.0 | 100.0 | 94.7 | 83.5 | 65.8 | 54.3 | 46.2 | **40.3** |

*Per cent. System size = annual generation as a share of annual consumption.*

**At 10% of consumption, 5.1 points separate the six profiles.** Every customer
absorbs almost everything a small system produces, including the night-heavy one —
because even a small array generates less, at midday, than almost any site draws.

**At 60%, the gap is 30.3 points.** The daytime customer still uses 71% of what it
generates; the night-heavy one uses 40%.

This is the finding that changes how the conversation should be run. The qualifying
question is not "would solar work here". At a small enough system it works for
everybody. The question is **how many kilowatt-peak this particular customer can
absorb** — and the answer varies by a factor of nearly two.

## 4. What that is worth as project size

The largest system that still lands inside a nine-year payback, at 1 000 EUR/kWp and
0.128 EUR/kWh avoided:

| Profile | Max system | kWp | Self-consumption there |
|---|---:|---:|---:|
| **Office hours, Mon–Fri** | 50% | **970** | 76.6% |
| Continuous 24/7 | 40% | 776 | 68.1% |
| Two shifts, Mon–Fri | 40% | 776 | 74.1% |
| Three shifts, Mon–Fri | 30% | 582 | 77.6% |
| Single shift, Mon–Fri | 30% | 582 | 72.8% |
| **Night-heavy, daily** | 30% | **582** | 65.8% |

Same consumption, same roof, same town: **1.67× the project** between the best and
worst shape.

Two honest caveats about this table. The nine-year hurdle is a choice — it sits inside
the range the model produces (7.6 to 10.0 years at this capex) so that it
discriminates between profiles instead of accepting or rejecting all of them. And the
sizes are the modelled steps, so the ranking is the durable result rather than the
exact kilowatt-peak.

## 5. Geography is the weaker filter

Same daytime profile, same system size, five Czech locations:

| Location | Yield (kWh/kWp) | Payback at 1 000 EUR/kWp |
|---|---:|---:|
| Brno | 1 087 | 8.1 |
| Prague | 1 055 | 8.3 |
| Plzeň | 1 031 | 8.6 |
| Ostrava | 1 026 | 8.6 |
| Ústí nad Labem | 997 | 8.8 |

Nine per cent of yield between the sunniest and dullest location in the country, worth
**0.7 years** of payback. At a fixed system size, the customer's own shape moves
payback by a comparable **0.6 years** — Plzeň and Ostrava, 5 kWh/kWp apart, land on
the same figure.

So on payback alone the two filters are similar. The difference is what they do to
project size: geography does not change how large a system the site can absorb, and
the profile changes it by 1.67×. Region is a tie-breaker. Operating hours decide the
project.

Worth noting for a targeting exercise: 9% is a small enough spread that no Czech
region should be written off for irradiance. The whole country is within 9% of itself.

---

## What would change these conclusions

- **Storage.** A battery decouples generation from consumption and would lift the
  night-heavy customer's self-consumption sharply. That is the product this analysis
  points those customers towards.
- **A different tariff structure.** If more of the network charge became volumetric,
  the avoided price would move towards 0.167 and every payback would shorten. If less,
  the reverse.
- **The capture rate continuing to fall.** At 0.62 and falling, export revenue is
  already a minor term. If it keeps going, self-consumption becomes the whole case and
  the profile matters more, not less.
- **Load shifting.** The model assumes consumption does not respond. A customer that
  moves a process into the middle of the day changes its own answer — which is a
  service worth selling.

## Reproducing this

```bash
python run_analysis.py
```

Eight seconds, offline, from the cached API responses in `data/raw/`. Every figure
above comes from `data/clean/findings.json`; the workbook and the deck read the same
file, and the workbook recomputes its default case in Excel formulas as a check on
both.
