# Rooftop solar: which customers, and how big

**The load profile does not decide whether a business should install solar. It
decides how large a system it can absorb before the surplus stops paying for
itself — and that is a qualifying question a sales team can answer from data it
already has.**

```bash
python run_analysis.py          # ~8 seconds, works offline from the cached data
```

---

## The question

An energy services business selling rooftop solar has to decide who to call first
and what to propose. Roof area and region are the obvious filters. This project
asks whether they are the right ones.

## The economics, in one paragraph

A kilowatt-hour the site consumes itself replaces one it would otherwise have
bought at the **retail** price — energy, taxes and a share of network charges. A
kilowatt-hour it exports earns only the **wholesale** price at that moment, and
solar generates precisely when wholesale prices are lowest.

For a Czech business customer in 2025 those two numbers are **0.128 EUR/kWh
avoided** against **0.038 EUR/kWh earned**: self-consumption is worth **3.4×** an
export. So the share of generation a site consumes itself is what decides the
investment — and that share depends on when the business runs, not on the roof. It is a
property of when
the business runs.

## The answer

A 2 000 MWh/year site, roof-mounted system facing south, modelled hour by hour for
a full year across six load profiles and five Czech locations.

**Share of generation consumed on site, as the system grows:**

| Profile | 10% system | 30% | 60% |
|---|---:|---:|---:|
| Continuous 24/7 | 100.0% | 80.8% | 51.9% |
| Three shifts, Mon–Fri | 97.6% | 77.6% | 50.7% |
| Two shifts, Mon–Fri 06:00–22:00 | 94.9% | 82.4% | 59.0% |
| Single shift, Mon–Fri 06:00–14:00 | 96.4% | 72.8% | 57.4% |
| **Office hours, Mon–Fri 08:00–18:00** | 96.1% | 83.7% | **70.7%** |
| **Night-heavy, daily 22:00–06:00** | 100.0% | 65.8% | **40.3%** |

*System size = annual generation as a share of annual consumption.*

**At a small system the profile barely matters.** Cover 10% of consumption and every
customer self-consumes almost everything — only 5.1 points separate the six profiles.
Anyone can be sold a small system.

**At a large one it decides the project.** At 60% the gap is 30.3 points. Within a
nine-year payback at 1 000 EUR/kWp, a daytime customer supports **970 kWp** against
**582 kWp** for a night-heavy one — **1.67× the project**, same consumption, same
roof, same town.

**And the export half is worth less every year.** Solar earned 0.89 of the baseload
price on the Czech wholesale market in 2021 and **0.62 in 2025**. More solar on the
system depresses the price in exactly the hours solar generates, so the gap between a
self-consumed and an exported kilowatt-hour widens with every year that passes.

**Geography is the weaker filter.** Across the five locations, yield runs 997 to 1 087
kWh/kWp — 9% end to end, worth 0.7 years of payback. At a fixed system size the
customer's own shape moves payback by about the same (0.6 years). The difference is that
geography does not change how large a system the site can absorb, and the profile
does. Region is a tie-breaker; operating hours decide the project.

The full write-up is in [`docs/FINDINGS.md`](docs/FINDINGS.md).

## What follows for a supplier

**Qualify on operating hours before roof area.** Operating hours are already in the CRM, or one
question away, and they predict the project size that a payback comparison alone
would not separate.

**Sell the size the customer can absorb.** Oversizing does not fail loudly. It quietly
converts 0.128 EUR/kWh of avoided cost into 0.038 EUR/kWh of export revenue. The
right proposal is the largest system that still lands inside the customer's own
payback hurdle — which is what the workbook in this repository computes.

**For the wrong shape, sell something else.** A night-heavy site does not become a
good solar customer by buying fewer panels. It becomes one by shifting load into the
day, or by storing. That is a different product, and this analysis identifies exactly
which customers need it.

---

## The workbook is meant to be used, not read

`output/rooftop_solar_targeting.xlsx` opens on a **Calculator** sheet: enter a
customer's annual consumption, a system size, a location, a load profile, an avoided
price and a capex, and it returns kWp, self-consumption, annual saving and payback —
all as formulas, with the self-consumption rate pulled out of the modelled grid by a
two-way INDEX/MATCH. A sales engineer can answer "what if we size it at 40% instead
of 30%" without anyone re-running Python.

The build script recomputes the default case independently and refuses to write the
file if it disagrees with `findings.json` by more than a fortnight of payback. The
finished workbook was then recalculated in a real spreadsheet engine and checked cell
by cell against the model: 582.07 kWp, 83.7% self-consumption, 68 069 EUR saved,
8.55 years.

## How it is built

| Step | Script | Output |
|---|---|---|
| 1. Fetch | `src/fetch_data.py` | `data/raw/*.json` — cached API responses |
| 2. Align | `src/build_dataset.py` | `data/clean/*.csv` |
| 3. Model | `src/analyse.py` | `data/clean/findings.json` |
| 4. Calculator | `src/build_excel_report.py` | `output/*.xlsx` |
| 5. Deck | `src/build_deck.py` | `output/*.pptx` |
| All of it | `run_analysis.py` | ~8 seconds |

**One source of truth.** Every number in the report, the workbook and the deck comes
from `findings.json`. Nothing downstream recalculates anything.

**Self-consumption is computed hour by hour** as `min(generation, load)`, never netted
over a month — netting would let August sunshine cancel a February night and would
overstate the result enormously.

**The template is read-only.** The deck generator substitutes `{{TOKEN}}` and swaps
chart placeholders, run by run, so the template's fonts and colours survive.

## Where the data comes from

| Source | What it provides |
|---|---|
| [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) (European Commission, JRC) | Hourly PV output for each location, SARAH3 satellite irradiance, 2023 |
| [energy-charts.info](https://energy-charts.info) (Fraunhofer ISE, CC BY 4.0) | Czech day-ahead prices — what an exported kWh earns |
| [Eurostat `nrg_pc_205_c`](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205_c) | Retail price split into energy, network and taxes — what a self-consumed kWh avoids |

43 800 modelled hours (5 locations × a full year). Method, every judgement call, and
how to verify any number are in [`docs/METHOD.md`](docs/METHOD.md).

## Three things that had to be right

**PVGIS timestamps are UTC**, and nothing in the response says so. It was verified
rather than assumed: for Brno at 16.606°E, solar noon falls at 10:53 UTC, and the
observed June output peaks in the hour labelled 10. Reading the series as local time
would shift generation two hours against the load — and self-consumption is precisely
a question of overlap.

**Generation and prices are joined on the UTC hour.** Joining on the local date and
hour looks natural and silently loses a row every year: on the October clock change
02:00 local happens twice and the two different hours collapse into one.

**The system is sized on the long-run yield rather than on 2023.** The hourly shape says
*when* the energy arrives; the long-run average says *how much a kilowatt-peak
delivers over its life*. Using 2023 for both would size the investment on one year's
weather — and it was the mismatch between these two that made the workbook and the
model disagree by half a month of payback until it was tracked down.

## Running it

```bash
pip install -r requirements.txt
python run_analysis.py              # from the cached data
python run_analysis.py --refresh    # re-download
```

Python 3.11+ (uses `zoneinfo`). `node` is only needed to rebuild the PowerPoint
template, which is committed.

## Where this stops being useful

- **Stylised load profiles rather than metered customer data.** A real site has shutdowns,
  seasonality and production peaks. The profiles and their assumptions are in
  `src/profiles.py` and travel into every output.
- **Simple payback**, undiscounted, before any subsidy, grant, tax treatment or
  maintenance cost. It compares customers; it does not model a project's finances.
- **Capex is a range and nowhere near a quote.** European commercial rooftop runs roughly
  700–1 300 EUR/kWp; the workbook takes it as an input for that reason.
- **What a self-consumed kWh avoids depends on the tariff.** Network charges are
  partly capacity-based and do not fall when consumption does, so the model runs
  three scenarios — 0.110, 0.128 and 0.167 EUR/kWh — and reports all three. The
  headline uses the middle one.
- **City-centre coordinates** stand in for a site in that region. A real project uses
  the roof's own orientation, pitch and shading survey.
- **One weather year** for the hourly shape. The solar resource varies about 5% year
  to year, which PVGIS reports and this repository carries through.

## Tools

Claude, ChatGPT and Gemini were part of the working set throughout — for background
reading on the market, for thinking through approaches, and to keep the code and the
writing moving. Every figure here was checked against its source before it was used.

`docs/METHOD.md` records what those checks found and changed, including what was wrong
in the first version. The report is the business output; this repository is what makes
it checkable — the raw API responses, the code that turns them into figures, and the
notes that say where the numbers stop being data and start being assumptions.
