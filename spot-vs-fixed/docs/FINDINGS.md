# Findings

Czech day-ahead electricity market, 2021 to August 2026. 73,775 settlement periods,
Czech local time, duration-weighted. Source: energy-charts.info (Fraunhofer ISE),
CC BY 4.0.

Every figure below is generated from `data/clean/findings.json`; none is typed by hand.

---

## 1. The intraday shape inverted

The average price by hour of day, indexed to each year's own baseload so the shape can
be read independently of the level:

| Hour | 2021 | 2026 |
|---|---:|---:|
| 03:00 | 71 | 112 |
| 08:00 | 121 | 122 |
| 13:00 | 99 | 49 |
| 20:00 | 120 | 169 |

*EUR/MWh, duration-weighted.*

In 2021 midday cost **38% more** than the small hours. In 2026 it costs **52% less**.
The cheapest hour of the day moved from 03:00 to 13:00. The most expensive hour moved
from 19:00 to 20:00 and got relatively more expensive.

The mechanism is not mysterious: solar output has pushed the middle of the day below
the night, and the evening peak now sits in the window where the sun has gone and
demand has not. What matters commercially is not the mechanism but that it happened
inside the term of a typical supply contract.

## 2. Which customer the market rewards, and when it changed

Profile factor against a flat 24/7 load = 1.00:

| Profile | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| Continuous 24/7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Three shifts, Mon–Fri | 1.045 | 1.050 | 1.049 | 1.053 | 1.045 | 1.053 |
| Two shifts, Mon–Fri 06:00–22:00 | 1.129 | 1.113 | 1.111 | 1.113 | 1.087 | 1.057 |
| Single shift, Mon–Fri 06:00–14:00 | 1.109 | 1.085 | 1.075 | 1.051 | 1.024 | 0.993 |
| **Office hours, Mon–Fri 08:00–18:00** | 1.119 | 1.072 | 1.052 | 1.014 | **0.976** | **0.916** |
| **Night-heavy, daily 22:00–06:00** | 0.940 | 0.962 | 0.965 | 0.972 | 0.986 | **1.025** |

Three things to read off it.

**The ends swapped.** In 2021 the night-heavy profile was 17.9 points cheaper than the
office profile. In 2026 it is 10.9 points more expensive. The office profile crossed
below the market average in 2025; the night profile crossed above it in 2026.

**The movement is monotonic.** Every profile moves the same direction every year from
2021 to 2026, through a gas crisis that tripled and then untripled the price level.
That is what makes it look structural rather than a run of weather.

**Shift patterns matter less than they look.** Three shifts on weekdays costs only 5%
over baseload, because once a site runs around the clock its shape is nearly flat. The
profiles that move are the ones concentrated in part of the day.

## 3. What the shape is worth

| Year | Cheapest shape | Dearest shape | Spread | At 10 GWh a year |
|---|---|---|---:|---:|
| 2021 | Night-heavy | Two shifts | 18.9 pp | 190,600 EUR |
| 2023 | Night-heavy | Two shifts | 14.5 pp | 146,200 EUR |
| 2025 | Office hours | Two shifts | 11.1 pp | 107,200 EUR |
| 2026 | Office hours | Two shifts | 14.2 pp | 156,800 EUR |

Two customers with the same annual volume, the same supplier and the same spot
contract are worth **157,000 EUR a year** apart in 2026, purely because of when they
consume. Note also which profile sits at the dearest end throughout: the two-shift
06:00–22:00 pattern straddles both the morning and evening peaks and misses the cheap
middle of the day — it is the shape the current market punishes most.

## 4. The advantage is seasonal, and that changes the product

Profile factors for 2026, computed against each season's own baseload:

| Profile | Summer (May–Aug) | Winter (Nov–Feb) |
|---|---:|---:|
| Office hours | **0.84** | **1.13** |
| Single shift | 0.96 | 1.09 |
| Two shifts | 1.03 | 1.12 |
| Night-heavy | 1.06 | 0.94 |

The daytime advantage is a solar advantage: it is worth 16% in summer and costs 13% in
winter. The annual factor of 0.92 is the average of two opposite regimes rather than a stable
state.

This is the finding with the most direct product consequence. A customer moved to spot
on the strength of the annual number will be delighted in June and hostile in January,
and the supplier will spend the winter defending a recommendation that was correct on
average. A seasonal or hybrid product describes reality; a flat one does not.

## 5. Volatility rose while the level did not

| Year | Baseload | Average daily spread | Worst day |
|---|---:|---:|---:|
| 2021 | 100.66 | 76.9 | 418.9 |
| 2022 | 247.43 | 183.4 | 520.2 |
| 2023 | 100.79 | 93.0 | 358.6 |
| 2024 | 85.11 | 112.9 | 737.3 |
| 2025 | 96.83 | 137.4 | 448.7 |
| 2026 | 110.69 | 174.9 | 707.0 |

*EUR/MWh. Daily spread = highest minus lowest price within a local day.*

2021 and 2026 have almost the same average price — 101 against 111 — but the average
day in 2026 spans **2.3 times** as much between its cheapest and dearest moment. The
shape effect is strengthening independently of the level.

The *average* day is the right measure here. The single widest day
in the period belongs to 2024 (737 EUR/MWh), and picking extremes would tell a story
about one day's weather rather than about the market. The average daily spread rises
every year without exception.

For a customer who can shift load, that is opportunity. For one who cannot, it is
risk, and it is the strongest available argument for what a fixed product is actually
selling. It is also an argument that does not depend on forecasting prices, which is
why it survives contact with a sceptical procurement manager.

## 6. Negative prices are now a routine midday event

| Year | Hours below zero | Share of period | Lowest price |
|---|---:|---:|---:|
| 2021 | 33 | 0.4% | −36 |
| 2023 | 134 | 1.5% | −69 |
| 2024 | 315 | 3.6% | −139 |
| 2025 | 323 | 3.7% | −224 |
| 2026 (Jan–Aug) | 266 | 4.6% | −500 |

They are concentrated between 10:00 and 16:00 — the same window that dragged the
midday price down. In those hours a customer able to move load is paid to consume.

Whether any given customer can do that depends on its process, which no public dataset
knows. But the size of the window — 266 hours in eight months — is large enough that
the question is worth asking of any customer with storage, pre-heating, pre-cooling or
batch production.

---

## What would change these conclusions

- **More storage on the system.** Batteries arbitrage exactly this spread, and at
  scale they would flatten the midday trough that the whole finding rests on.
- **A different evening peak.** The expensive hours have moved later each year; if
  that continues, the two-shift profile gets worse and the single-shift profile better.
- **Weather.** One cloudy summer would dent the seasonal figures. Four consecutive
  years moving the same way is why this reads as structural, but it is still four years.
- **The customer's own behaviour.** The profile factor assumes consumption does not
  respond to price. A customer that moves load in response to a spot contract changes
  its own factor, which is the point of offering one.

## Reproducing this

```bash
python run_analysis.py
```

Six seconds, offline, from the cached API responses in `data/raw/`. Every figure above
comes from `data/clean/findings.json`; the workbook and the deck read the same file.
The workbook goes further and recomputes the factors in Excel formulas, which the
build script checks against the report before writing it.
