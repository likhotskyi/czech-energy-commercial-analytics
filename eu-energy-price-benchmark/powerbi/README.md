# Power BI model

A star schema over the same cleaned data the report and the workbook use, built
by `src/build_powerbi_model.py` so it regenerates whenever Eurostat is refreshed.

The point of a dashboard here, rather than another chart: the static report answers
the question for one band in one country. A key account manager needs the answer for
*their* customer — a different band, sometimes a different market. That is a slicer,
not a chart.

## The model

```
      dim_country ──┐                    ┌── dim_year
      dim_band ─────┼── fact_prices      │
      dim_period ───┘                    ├── fact_components ── dim_component
```

| Table | Rows | Grain |
|---|---:|---|
| `fact_prices` | 2 775 | country × band × period × commodity |
| `fact_components` | 63 | country × year (unpivots to 185 in Power Query — four Eurostat nulls are dropped) |
| `dim_country` | 7 | with a `role` column: Home / Peer / Reference |
| `dim_band` | 11 | with `band_order`, electricity and gas |
| `dim_period` | 38 | half-yearly, with `period_sort` |
| `dim_year` | 9 | annual, for the components only |
| `dim_component` | 3 | with `set_by`: Supplier / Regulator / State |

Four decisions worth defending:

**Two fact tables, two time dimensions.** Prices are half-yearly, components annual.
Forcing both onto one date table needs a many-to-many relationship and lets a user
filter to `2025-S1` and see a full-year component figure with no warning. Separate
grains, separate dimensions, separate pages.

**`dim_country[role]` rather than country names in measures.** Rankings must exclude
the EU average — it is an aggregate, not a country. A measure that filters on
`role <> "Reference"` keeps working when a label changes; one that names
`"EU average"` does not.

**`dim_component[set_by]`** carries the whole commercial point in the model itself:
who sets that part of the price. Colour a stacked bar by it and the chart says
"this much is ours, that much is not" without a caption.

**`dim_band[band_order]`.** Consumption bands sort alphabetically otherwise, which
puts `20-499 MWh` before `2 000-19 999 MWh` and turns the size curve into noise. Set
*Sort by column* on `band_name` before building any visual.

One band — gas above 1 000 000 GJ — is dropped: Eurostat publishes nothing for it in
these countries, and a dimension row with no facts adds an empty category to every
visual. The build script reports the drop rather than doing it silently.

## What is in the report

**Page 1 — where Czechia sits.** Slicers for country, commodity and band. Cards for
the price, the gap to the EU average, the gap to Germany, and the rank among
neighbours. Price over time by country; the ranking at the latest period; and the
price-by-band curve, which is the visual that needs `band_order` to mean anything.

**Page 2 — what the bill is made of.** The price split into energy, network and
taxes, by country. A What-If slider for the discount a supplier might offer, and two
cards that translate it: what it takes off the customer's bill, and what it costs in
euros a year for a 2 000 MWh site.

## Files

| File | What it is |
|---|---|
| `fact_*.csv`, `dim_*.csv` | the model |
| `measures.dax` | every measure, with a comment on what it does and why |
| `power_query.m` | the unpivot step, done in Power Query rather than Python so it is visible in the query editor |
| `theme-large.json` | the report theme: type sizes, and the same three colours the report and the deck use |
| `czech-energy-prices.pbix` | the finished report |

`fact_components.csv` is deliberately left wide. Unpivoting it is a one-step
transformation, and doing it in Power Query puts it where a reviewer looks.

Rebuild the model with:

```bash
python src/build_powerbi_model.py
```

## The theme

`theme-large.json` is applied through *View > Themes > Browse for themes*. It sets
the type scale once for the whole report — 34pt on card values, 17pt titles, 14pt
axes and legends, against Power BI's 9-10pt defaults — and pins the three component
colours to the ones the written report and the deck already use: blue for energy,
green for network, orange for taxes. A reader moving between the three should never
have to work out that the blue bar means the same thing in each.

## Two interactions worth knowing about

The country slicer does not filter the ranking chart, and the customer-size slicer
does not filter the size curve. Both are set through *Format > Edit interactions*.
Without them, picking Czechia collapses the ranking to a single bar and picking a
band collapses the curve to a single point — the two visuals whose whole job is
to put the selection in context.
