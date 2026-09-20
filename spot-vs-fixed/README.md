# Spot or fixed? The answer changed

**What a business customer's own consumption shape does to the price it pays on the
Czech day-ahead market — and why the right product for a daytime customer has
reversed since 2021.**

```bash
python run_analysis.py          # ~6 seconds, works offline from the cached data
```

---

## The question

A supplier sells the same electricity to every customer, but it sells it two ways: at
a fixed price, or indexed to the day-ahead market. Steering each customer to the
right one is a commercial decision made thousands of times a year, usually from a
rule of thumb.

The rule of thumb most people carry is *daytime power is expensive, night power is
cheap*. It was true for decades. This project asks whether it still is, and what it
is worth to get the answer right.

## The one number everything hangs on

A customer does not pay the average market price. It pays the average price
**weighted by its own consumption**, which is a different number whenever its
consumption is not flat. The ratio between the two is the profile factor:

```
                     Σ (price × load × duration)
profile factor  =    ───────────────────────────   ÷   baseload price
                          Σ (load × duration)
```

- **1.00** — the customer consumes the market average. A flat 24/7 load is 1.00 by
  definition, which makes it the natural benchmark.
- **above 1.00** — the customer consumes when power is expensive; its shape costs it
  money.
- **below 1.00** — the customer consumes when power is cheap; its shape earns it money.

Six stylised profiles are modelled, each a recognisable kind of customer, from a
continuous foundry to an office building to a cold store that pre-cools overnight.
The assumptions behind each are in [`src/profiles.py`](src/profiles.py) and travel
with the results into every output.

**What the factor does not settle.** It says nothing about whether spot beats fixed. A real fixed
offer also contains a forward price, a risk premium and balancing costs, none of
which are public. The factor isolates the *shape* effect — the part that differs
between two customers buying the same volume from the same supplier in the same
year. That is a defensible number; "spot is X% cheaper" would not be.

## The answer

Czech day-ahead market, 73,775 settlement periods, 2021 to August 2026.

| Profile | 2021 | 2026 | Change |
|---|---:|---:|---:|
| Continuous 24/7 | 1.000 | 1.000 | — |
| Three shifts, Mon–Fri | 1.045 | 1.053 | +0.8 pp |
| Two shifts, Mon–Fri 06:00–22:00 | 1.129 | 1.057 | −7.2 pp |
| Single shift, Mon–Fri 06:00–14:00 | 1.109 | 0.993 | −11.6 pp |
| **Office hours, Mon–Fri 08:00–18:00** | **1.119** | **0.916** | **−20.4 pp** |
| **Night-heavy, daily 22:00–06:00** | **0.940** | **1.025** | **+8.5 pp** |

**The two ends of the table swapped places.** In 2021 the night-heavy customer had
the cheap shape, 17.9 points below the daytime one. In 2026 it is 10.9 points above
it. The daytime profile crossed below the market average in 2025; the night profile
crossed above it in 2026.

**Why.** Midday cost **+38%** against the small hours in 2021. In 2026 it is **−52%**.
The cheapest hour of the day used to be 03:00; it is now 13:00. Solar output has
pushed the middle of the day below the night, and the expensive hours have moved to
the evening peak at 20:00, when the sun has gone and demand has not.

**What it is worth.** In 2026 there are 14.2 points between the best and worst shape
— 15.7 EUR/MWh, or **157,000 EUR a year** for a customer taking 10 GWh. Two customers
with identical annual volume, identical contract and identical supplier.

**But it is a season rather than a settled state.** Across summer 2026 the office profile is **0.84**.
Across winter it is **1.13**. The advantage is a solar advantage and it reverses when
the sun does. Any product built on the annual number alone will be resented every
January.

The full write-up is in [`docs/FINDINGS.md`](docs/FINDINGS.md).

## What follows for a supplier

**Price the shape as well as the volume.** A fixed offer quoted off the baseload for
both customers above mis-prices both: too dear for the daytime one, too cheap for
the night one. The shape is knowable in advance from the customer's own metering.

**The daytime customer is the one to approach about spot — seasonally.** Single-shift
and office-hours loads now sit below the market average and are still moving. The
honest product is seasonal or hybrid. A flat promise is the kind a customer resents
every January. And a competitor can make
the same argument, so this cuts both ways.

**Certainty is worth more than it was.** The average day now spans 175 EUR/MWh
between its cheapest and dearest moment, against 77 in 2021 — while the annual
average barely moved (101 then, 111 now). The shape effect is getting stronger
independently of the price level, which makes the risk premium on a fixed product
easier to justify to a customer who cannot move load.

---

## How it is built

| Step | Script | Output |
|---|---|---|
| 1. Fetch | `src/fetch_prices.py` | `data/raw/day_ahead_CZ_*.json` — cached API responses |
| 2. Build one comparable series | `src/build_dataset.py` | `data/clean/prices.csv`, `coverage.csv` |
| 3. Analyse | `src/analyse.py` | `data/clean/findings.json` |
| 4. Workbook | `src/build_excel_report.py` | `output/*.xlsx` |
| 5. Deck | `src/build_deck.py` | `output/*.pptx` |
| All of it | `run_analysis.py` | ~6 seconds |

**One source of truth.** Every number in the report, the workbook and the deck comes
from `findings.json`. Nothing downstream recalculates anything and no figure is typed
by hand, so the three cannot disagree with each other.

**The workbook computes, it does not display.** The profile factors in
`output/*.xlsx` are SUMPRODUCT formulas over a price grid, with the load weights
pulled in by INDEX/MATCH from an editable table. Change the office base load from 15%
to 25% and all 36 factors recalculate. The build script checks the workbook's own
arithmetic against `findings.json` before writing the file and refuses to ship one
that disagrees — which is how a genuine bug was caught: the weight columns were
originally written beside the table rather than inside it, so every
`Grid[w_office]` reference resolved to `#NAME?` in Excel while the Python numbers
looked perfect.

**The template is read-only.** `templates/report_template.pptx` is treated the way a
brand-team template is: the generator only substitutes `{{TOKEN}}` and swaps
`{{CHART:name}}` placeholders for rendered charts, run by run so the template's fonts
and colours survive.

**The raw downloads are cached and committed**, so the analysis runs offline and
reproduces these exact numbers later. `--refresh` re-downloads.

## Two things that had to be right

Both would have produced a plausible wrong answer rather than an error, which is why
they are checked rather than assumed.

**Local time.** The API timestamps in UTC. Every question here is about when a factory
runs, and a factory runs on Czech local time. Reading UTC as local shifts the analysis
one hour in winter and two in summer — enough to move the midday trough into the wrong
shift. Conversion uses the Europe/Prague zone so daylight saving is handled by the
zone database rather than an assumed offset.

**Unequal settlement periods.** The Czech market moved from hourly to 15-minute
settlement on 1 October 2025. From that date each row covers a quarter of an hour, so
a plain average weights an October quarter-hour the same as a January hour. Every
average here is duration-weighted; the script prints the difference, and it is zero
for every single-resolution year and 3.5% for 2025, which is the year that spans the
switch. A result that is exactly zero where it must be is worth more than an assertion.

Delivered hours are also checked against the calendar year — 8 760 in a normal year,
8 784 in 2024 — so a missing day cannot pass as a complete year.

## Running it

```bash
pip install -r requirements.txt
python run_analysis.py              # from the cached data
python run_analysis.py --refresh    # re-download
```

Python 3.11+ (uses `zoneinfo`). `node` is only needed to rebuild the PowerPoint
template, which is committed.

## Where the data comes from

Day-ahead auction prices for the Czech bidding zone from
[energy-charts.info](https://energy-charts.info), operated by Fraunhofer ISE,
licence **CC BY 4.0**. A spot-indexed contract settles against this auction, which is
what makes the comparison real rather than illustrative.

Method, every judgement call, and how to verify any number by hand are in
[`docs/METHOD.md`](docs/METHOD.md).

## Where this stops being useful

- **Stylised profiles rather than metered data.** A real site has seasonality, shutdowns,
  production peaks and its own weekly rhythm. The sensitivity analysis in
  `findings.json` shows how much the answer depends on the assumptions: with the
  overnight base load switched off entirely, the office factor runs 1.19 → 0.87
  instead of 1.12 → 0.92 — the same direction, roughly twice the size.
- **Shape only.** This is not a product comparison. Forward prices, risk premia and balancing
  costs are not public and are not modelled.
- **History rather than forecast.** These figures show where the market has moved, not
  where it will be when a three-year contract ends. The direction has been consistent
  for four years. That is evidence; it is not a guarantee.
- **2026 covers January to August**, and is labelled as partial everywhere it appears.
- **Nothing about margin.** The profile factor is what a customer pays. What a
  supplier earns.

## Tools

Claude, ChatGPT and Gemini were part of the working set throughout — for background
reading on the market, for thinking through approaches, and to keep the code and the
writing moving. Every figure here was checked against its source before it was used.

`docs/METHOD.md` records what those checks found and changed, including what was wrong
in the first version. The report is the business output; this repository is what makes
it checkable — the raw API responses, the code that turns them into figures, and the
notes that say where the numbers stop being data and start being assumptions.
