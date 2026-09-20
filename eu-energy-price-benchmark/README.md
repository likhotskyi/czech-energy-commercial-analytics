# What a Czech industrial electricity bill is made of

**And how much of it a supplier can actually compete on.**

A reproducible market analysis built on real Eurostat data: Czechia benchmarked
against its five neighbouring markets and the EU average, from the raw API
response through to a spreadsheet and a slide deck.

```bash
python run_analysis.py          # ~3 seconds, works offline from the cached data
```

---

## The question

An energy retailer selling to Czech industry has to answer two things before it can
price anything:

1. **Where does Czechia sit?** If a Czech factory is paying far more than its German
   parent company's plant, that is a retention problem. If far less, it is a sales argument.
2. **How much of the bill is even ours?** A supplier sets the energy and supply
   component. Network charges are set by the regulator and taxes by the state — they are
   identical whichever supplier the customer signs with. A discount only reaches the
   customer through the part the supplier controls.

Question 2 is the one most price comparisons skip, and it is the one that decides
whether competing on price is worth doing at all.

## The answer

Latest data: **2025-S2**, mid-size industrial band (2 000–19 999 MWh a year), excluding VAT.

| | |
|---|---|
| Czech price | **16.36 EUR cents/kWh** |
| vs the EU average | **+2.5%** |
| vs Germany | **−14.9%** |
| Rank among its 6 neighbouring markets | **cheapest of six** |
| Commodity share of the bill | **66.1%** (EU average 62.5%, Poland 45.5%) |
| What a 10% commodity discount takes off the total bill | **6.6%** (Germany 5.3%, Poland 4.6%) |
| Still above pre-crisis (2021-S2) | **+64.9%** |

**Three things follow.**

**1. Price competition has more leverage in Czechia than next door.** With 66% of the
bill in the supplier's hands — the highest share of the seven markets compared — a
discount reaches the customer's total cost more directly than in Poland, where nearly
half the bill is tax that no supplier can touch. The same headline discount costs the
same margin and buys more visible saving.

**2. The largest consumers are the exposed segment.** Across the EU the large band pays
59% less per kWh than the smallest. In Czechia the gap is 34%. Worse, the Czech curve
turns back up: consumers above 20 000 MWh pay *more* per kWh than the 2 000–19 999 MWh
band. Large industrial accounts get less volume benefit here than their EU peers — and
they are exactly the group able to tender across borders.

**3. Against Germany, sell the gap; against the EU, sell stability.** Czechia is 15%
below Germany but slightly above the EU average, so "cheap energy" is only a credible
pitch when the comparison is a neighbour. What is credible more widely is that Czech
prices moved less violently through 2022–23 than any neighbour's.

Gas tells a similar story: Czech industrial gas is 6.1% below the EU average and second
cheapest of the six.

The full write-up, with the reasoning and the caveats, is in
[`docs/FINDINGS.md`](docs/FINDINGS.md).

---

## The part worth reading if you only read one thing

Eurostat publishes business electricity prices twice: as a headline price series and as
a breakdown into components. **They do not agree if you add the components up.**

```
Energy & supply + Network costs + "Taxes, fees, levies and charges"
   = 20.2 cents/kWh   ... but the published price is 16.5 cents/kWh
```

The naive sum overstates the industrial price by **21%**. The reason is that Eurostat's
tax total already contains VAT, which the headline series excludes. Subtract it and the
two sources agree to a **median of 0.75%**.

That one line decides everything downstream. Skip it and the commodity share comes out
at about 55% instead of 66% — wrong, but not obviously wrong.

The check runs on every execution rather than sitting in a comment. It is written to
`data/clean/reconciliation.csv` as evidence, and **the pipeline refuses to produce a
report if the two sources ever drift more than 3% apart**:

```python
if median_deviation > 3:
    raise RuntimeError(
        "Components no longer reconcile with the headline series. "
        "Do not publish these numbers until the cause is understood."
    )
```

## Two more checks that changed a conclusion

**Gas prices are published in two units.** Eurostat serves the same gas series in both
kWh and gigajoules. Querying without pinning the unit returns every country twice, in
two different magnitudes — and an average over that mixture is meaningless while still
looking sane. The query pins `unit=KWH`, and `build_dataset.py` additionally asserts that
one country/band/period yields exactly one price.

**"The largest band" is not the same band in every country.** Czechia does not publish
the ≥150 000 MWh band at all — too few consumers to report without identifying them. The
first version of this analysis compared each country's own largest available band, which
silently compared Czechia's 70 000–149 999 MWh against Germany's ≥150 000 MWh. The size
discount is now measured between bands **every** country reports, the choice is recorded
in the output, and countries whose price curve is non-monotonic are flagged rather than
smoothed over.

Both of these produced numbers that looked fine. Neither would have been caught by
looking at the chart.

---

## How it is built

| Step | Script | Output |
|---|---|---|
| 1. Fetch | `src/fetch_data.py` | `data/raw/*.json` — cached API responses |
| 2. Tidy & reconcile | `src/build_dataset.py` | `data/clean/*.csv` |
| 3. Analyse | `src/analyse.py` | `data/clean/findings.json` |
| 4. Spreadsheet | `src/build_excel_report.py` | `output/*.xlsx` |
| 5. Deck | `src/build_deck.py` | `output/*.pptx` |
| All of it | `run_analysis.py` | ~3 seconds |

**One source of truth.** Every number in the report, the workbook and the deck comes from
`findings.json`. Nothing downstream recalculates anything and no figure is typed by hand,
so the three artefacts cannot disagree with each other — which is the usual way a
recurring report ends up embarrassing somebody. When Eurostat revises a series, one run
updates all three together.

**The raw responses are cached and committed.** The analysis runs offline and reproduces
the exact numbers in this README months from now, after Eurostat has revised the series.
`--refresh` re-downloads.

**The spreadsheet is alive.** Summary sheets are built from live `AVERAGEIFS` / `SUMIFS`
formulas over named Excel tables. Nothing is pasted in as a value by Python. Filter the data,
add a country, drop in your own PivotTable — everything recalculates. A workbook of
hard-coded values is dead the first time someone edits it.

**The template is read-only.** `templates/report_template.pptx` is treated the way a
brand-team template is: the generator only substitutes `{{TOKEN}}` and swaps
`{{CHART:name}}` placeholders for rendered charts. Replacement happens run by run, never
by assigning to a paragraph's text — that collapses the paragraph into a single unstyled
run and silently destroys the template's fonts and colours. `templates/build_template.js`
rebuilds the template so the demo is self-contained; in a real deployment you delete it
and drop in the company's own file.

**Chart colours were checked before use.** The categorical palette was tested for
colour-vision-deficiency separation and contrast against the surface. No chart has two
value axes, single-series charts carry no legend, and the subject country is the only
coloured line — the rest are recessive grey, because a chart should have a subject.

## Running it

```bash
pip install -r requirements.txt
python run_analysis.py              # from the cached data
python run_analysis.py --refresh    # re-download from Eurostat
```

Python 3.11+. `node` is only needed to rebuild the PowerPoint template, which is committed.

## Where the data comes from

All from [Eurostat](https://ec.europa.eu/eurostat/web/energy/database), last updated
2026-08-11:

| Dataset | What it is |
|---|---|
| [`nrg_pc_205`](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205) | Electricity prices for non-household consumers, half-yearly since 2007, by consumption band |
| [`nrg_pc_205_c`](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205_c) | The same price split into components, annual since 2017 |
| [`nrg_pc_203`](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_203) | Gas prices for non-household consumers |

2 775 price observations in total. Method, every judgement call, and how to verify any
number by hand are in [`docs/METHOD.md`](docs/METHOD.md).

## Where this stops being useful

- These are **national averages**. An individual contract depends on the load profile,
  the hedging strategy, and the date it was signed. This analysis sizes a market; it does
  not price a deal.
- Band boundaries are **consumption-based**, so a country's industrial mix affects its
  average within a band. Czechia's heavy-industry share is not the same as Austria's.
- Half-yearly data **cannot show** what a spot-exposed customer paid in a given month —
  precisely the customers who suffered most in 2022.
- The commodity share is **what a supplier prices**, which is a different thing from what it
  earns. Nothing here says
  anything about anyone's margin.
- Czechia's ≥150 000 MWh band is **not published**, so the very largest consumers are
  invisible in this data. Any conclusion about them is an inference from the band below.

## Tools

Claude, ChatGPT and Gemini were part of the working set throughout — for background
reading on the market, for thinking through approaches, and to keep the code and the
writing moving. Every figure here was checked against its source before it was used.

`docs/METHOD.md` records what those checks found and changed, including what was wrong
in the first version. The report is the business output; this repository is what makes
it checkable — the raw API responses, the code that turns them into figures, and the
notes that say where the numbers stop being data and start being assumptions.
