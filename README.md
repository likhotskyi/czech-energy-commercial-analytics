# AI-Assisted Commercial Analytics for the Czech B2B Electricity Market

Three analyses of one commercial question: **where does a Czech energy retailer
actually have room to compete for a business customer, and which customer is
worth competing for?**

Each part stands on public data, its own code and its own written method. Every
figure traces back to a source API.

| | Part | The question | The answer |
|---|---|---|---|
| 1 | [**Pricing** — what the bill is made of](eu-energy-price-benchmark) | How much of an industrial electricity bill can a supplier actually price? | **66.1%**. So a 10% commodity discount moves the customer's bill by 6.6%, not 10% |
| 2 | [**Procurement** — spot against fixed](spot-vs-fixed) | Which customer does the wholesale market reward, and has that changed? | It inverted. An office load went from **+11.9%** above baseload in 2021 to **−8.4%** below it in 2026 |
| 3 | [**Solar** — who to sell it to](solar-self-consumption) | Which customer can absorb rooftop solar, and what is a kilowatt-hour worth to them? | Power used on site is worth **3.4×** power exported. Load profile changes viable system size by **1.67×**; geography by 9% |

## How they connect

Part 1 sizes the prize. Only two thirds of a Czech industrial bill is set by the
supplier at all — network charges and taxes are set by the regulator and by law.
If that share were 45%, as it is in Poland, price competition would barely reach
the customer.

Part 2 asks what those two thirds are worth to *this* customer rather than to an
average one. The same market charges different customers different effective
prices depending on when they consume, and solar has reversed which customer is
the cheap one. On a 10 000 MWh contract the gap between the best and the worst
load profile has been worth €120k–€374k a year.

Part 3 takes the same logic to an adjacent product. A solar kilowatt-hour
consumed on site avoids the retail price; exported, it earns the wholesale price
at the moment solar is abundant and power is cheap. So sizing a system is a
load-profile question before it is a roof question.

## What is in each folder

```
eu-energy-price-benchmark/   Eurostat prices and components, Power BI model, report, workbook
spot-vs-fixed/               Czech day-ahead prices 2021-2026, six load profiles, report, workbook
solar-self-consumption/      PVGIS hourly generation, self-consumption model, report, calculator
```

Each folder has its own `README.md`, a `docs/METHOD.md` that says how every
number is produced and what was got wrong on the way, a `docs/FINDINGS.md` with
the numbered findings and their limits, and a `run_analysis.py` that rebuilds
every figure in the report from the source APIs.

## Tools and verification

Claude, ChatGPT and Gemini were part of the working set throughout — for
background reading, for thinking through approaches, and to keep the code and
the writing moving.

What matters more is what happened to the output. Every headline figure was
re-fetched from the source API in a separate pass and compared with the stored
result. Two of those re-checks disagreed on the first attempt, and both
disagreements turned out to be in the re-check rather than in the stored figure:
a wrong tax basis on the Eurostat query, and free-standing instead of
roof-mounted on PVGIS. Working out why two numbers differ is the part that
matters. [`VALIDATION.md`](eu-energy-price-benchmark/VALIDATION.md) records all
of it.

Several mistakes survived the first draft and were caught by checking rather
than by reading — a component sum that overstated the industrial price by 21.2%
because the Eurostat tax line includes VAT; a workbook that returned `#NAME?`
because helper columns sat beside a named table instead of inside it, which the
Python tests could not see because Python does not evaluate Excel formulas; a
join that silently lost the duplicated hour at the end of summer time. Each is
written up in the method notes.

Where a number rests on an assumption rather than on data — capex per
kilowatt-peak is the clearest case — it is an input cell in the workbook rather
than a constant in the code, and the report says how sensitive the answer is
to it.

## Built with

Python (pandas, requests) · Power BI (star schema, DAX, Power Query) ·
Excel (live formulas over named tables) · matplotlib · python-pptx

## Data

Eurostat (`nrg_pc_205`, `nrg_pc_205_c`, `nrg_pc_203`) · energy-charts.info,
Fraunhofer ISE, CC BY 4.0 · PVGIS v5.3 SARAH3, European Commission JRC.
Attribution and licence terms are in each folder's `NOTICE.md`.

**Not forecasts and not investment advice.** Each part ends with a section on
where its conclusions stop holding.
