# Method

Everything here is a judgement call that could have gone another way. This file
records what was chosen and why.

---

## 1. The data

Three Eurostat datasets, all served through the public dissemination API, all cached
in `data/raw/` as the exact JSON the API returned.

| Dataset | Frequency | Coverage | Used for |
|---|---|---|---|
| `nrg_pc_205` | half-yearly | 2007-S1 – 2025-S2 | headline price, all consumption bands |
| `nrg_pc_205_c` | annual | 2017 – 2025 | the split into energy / network / tax |
| `nrg_pc_203` | half-yearly | 2007-S1 – 2025-S2 | gas, the second commodity |

**Why these and not a price index?** Because the question is about the *composition* of
the bill, and `nrg_pc_205_c` is the only public source that decomposes it consistently
across countries.

### Reading the API

Eurostat returns JSON-stat 2.0. It is compact and not obvious:

```json
{
  "id":   ["freq", "siec", "nrg_cons", "unit", "tax", "currency", "geo", "time"],
  "size": [1, 1, 1, 1, 1, 1, 7, 38],
  "value": { "0": 0.1234, "3": 0.1567, ... }
}
```

`value` is a **sparse** map from a flat index to a number. To recover which observation
`"3"` is, the index has to be decoded against the dimension sizes in row-major order —
the last dimension varies fastest. Missing observations are simply *absent*; there are no
nulls. `src/eurostat.py` does this decoding and returns a tidy frame with gaps, rather
than a dense matrix with invented zeros.

If you ever see a suspiciously round zero in Eurostat-derived work, this is usually why.

---

## 2. The choices that move the numbers

### Excluding VAT

**Choice:** all prices exclude VAT (`tax=X_VAT`).

**Why:** VAT is recoverable for a business. Including it measures something no company
actually pays. This single parameter changes the country ranking, because VAT rates
differ by more than the underlying price gaps in some pairs.

**Consequence:** these figures are *not* comparable to household price headlines in the
press, which normally include VAT.

### Band ID (2 000–19 999 MWh a year) as the focus

**Choice:** the headline comparison uses one band.

**Why:** this is the mid-size industrial customer — a medium factory, a large logistics
site, a hospital. Large enough to negotiate a contract, numerous enough to constitute a
market. The "all bands" aggregate mixes a corner shop with a smelter and is dominated by
whichever the country has more of, so it compares industrial structures rather than prices.

**Consequence:** a conclusion about band ID is not automatically a conclusion about the
whole market. `src/analyse.py` computes the full band curve separately for exactly this
reason.

### EUR, not purchasing power standards

**Choice:** prices in EUR.

**Why:** a factory pays its electricity bill in money, and competes for orders against
other factories in money. PPS is the right unit for asking whether households can afford
electricity; it is the wrong unit for industrial cost competitiveness.

**Consequence:** a country with a weaker currency looks cheaper here than it would in PPS.
For a cost-competitiveness question that is exactly what you want to see.

---

## 3. The reconciliation, in full

This is the check that matters most, so here it is in detail.

Eurostat publishes the same price twice — as a level and as a decomposition — and a
reader naturally assumes the parts sum to the whole. For Czechia, 2025:

| Component | EUR/kWh |
|---|---|
| `NRG_SUP` — energy and supply | 0.1102 |
| `NETC` — network costs | 0.0385 |
| `TAX_FEE_LEV_CHRG` — taxes, fees, levies and charges | 0.0529 |
| **Naive sum** | **0.2016** |
| Published price (`nrg_pc_205`, 2025 average, excl. VAT) | **0.1646** |
| Error | **+22%** |

The tax line is a *total* that already contains VAT. The itemised tax components confirm it:

| | EUR/kWh |
|---|---|
| `TAX_RNW` — renewable taxes | 0.0166 |
| `TAX_ENV` — environmental taxes | 0.0012 |
| `OTH` — other | 0.0001 |
| Sum of actual taxes excluding VAT | **0.0179** |
| `VAT` | 0.0350 |
| 0.0179 + 0.0350 | **0.0529** = `TAX_FEE_LEV_CHRG` exactly |

So the correct reconstruction is:

```
price excluding VAT = NRG_SUP + NETC + (TAX_FEE_LEV_CHRG − VAT)
```

which gives 0.1666 against a published 0.1646 — a 1.2% gap, explained by the components
being annual while the price series is half-yearly and volume-weighted differently.

Run across all seven countries and all nine years:

| Method | Median absolute deviation from the published series |
|---|---|
| Naive sum | **21.2%** |
| Subtracting VAT | **0.75%** |

**This check runs on every execution** and is written to `data/clean/reconciliation.csv`
with both methods side by side. If the median deviation ever exceeds 3%, the pipeline
raises and refuses to produce a report — because the most likely cause is Eurostat
changing a definition, and the second most likely is a bug, and in neither case should
slides come out of it.

---

## 4. The two bugs this project caught, and what they teach

### Duplicated gas observations

Eurostat serves gas prices in **both kWh and gigajoules**. A query that does not pin
`unit` returns every country twice, at two magnitudes roughly 3.6× apart. Any average
over that mixture is meaningless — and it is *plausible*, which is what makes it
dangerous. It sits between the two real values and no chart looks wrong.

Fixed in two places on purpose: the query pins `unit=KWH`, and `build_dataset.py`
independently asserts that one country/band/period yields exactly one observation. The
query is the fix; the assertion is what catches the next version of this mistake.

### Comparing different bands and calling it a comparison

The first version measured the "size discount" as each country's **largest available
band** against its smallest. That silently compared Czechia's 70 000–149 999 MWh figure
against Germany's ≥150 000 MWh figure, because **Czechia does not publish the top band at
all** — too few consumers to report without identifying them.

It was caught by looking at the rendered chart and noticing the Czech line ended one step
short of everyone else's, and higher than its own previous point.

Now the discount is measured between the smallest band and **the largest band every
country in the comparison reports**, the chosen pair is recorded in the output
(`measured_between`), and any country whose price curve rises with size is flagged in
`non_monotonic_curves` rather than averaged away.

The corrected number is different and the conclusion survived — but it might not have,
and that is the point.

---

## 5. How to verify any number here by hand

Nothing in this repository requires trust. Every figure can be checked against Eurostat's
own interface in a couple of minutes.

**The headline Czech price.**
Open [`nrg_pc_205` in the Eurostat data browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205),
set consumption to *2 000 MWh – 19 999 MWh (band ID)*, tax to *Excluding VAT and other
recoverable taxes and levies*, currency to *Euro*, time to *2025-S2*, geo to *Czechia*.
You should see **0.1636**.

**The component split.** Same browser,
[`nrg_pc_205_c`](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205_c),
band ID, EUR, 2025, Czechia. Energy and supply **0.1102**, network **0.0385**, taxes
total **0.0529**, VAT **0.0350**. Then `0.1102 + 0.0385 + (0.0529 − 0.0350) = 0.1666`.

**Straight from the API**, no browser:

```bash
curl -s "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_205\
?format=JSON&lang=en&geo=CZ&nrg_cons=MWH2000-19999&currency=EUR&tax=X_VAT&time=2025-S2" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['value'])"
```

**Against the cached copy in this repository**, which is what the report was built from:

```bash
python3 -c "
import sys; sys.path.insert(0,'src')
import json, eurostat
df = eurostat.to_frame(json.load(open('data/raw/nrg_pc_205.json')))
print(df.query(\"geo=='CZ' and nrg_cons=='MWH2000-19999' and time=='2025-S2'\"))"
```

If the live API and the cached copy ever disagree, Eurostat has revised the series —
which is the reason the cache exists.

---

## 6. Known limitations

- **National averages.** This sizes a market; it does not price a deal. An individual
  contract turns on load profile, hedging and signature date.
- **Industrial mix inside a band.** Band boundaries are consumption-based, so a country's
  average within a band reflects what kind of companies it has, not only what it charges.
- **Half-yearly granularity.** Cannot show what a spot-exposed customer paid in a given
  month — exactly the customers hit hardest in 2022.
- **Nothing about margin.** The commodity share is what a supplier *prices*, not what it
  *earns*.
- **The top band is missing for Czechia.** Any statement about the very largest Czech
  consumers is an inference from the band below, and is labelled as such.
- **Components are annual.** The composition figures are a year's average; the price
  figures are a semester. They reconcile without being identical, and the residual gap is
  reported rather than hidden.
