# Findings

Czech industrial energy prices benchmarked against Austria, Germany, Hungary, Poland,
Slovakia and the EU average. Source: Eurostat, last updated 2026-08-11. Latest
observation 2025-S2. All prices exclude VAT, which is recoverable for a business.

Unless stated otherwise, figures are for the mid-size industrial band — 2 000 to
19 999 MWh a year. Every number below is generated from `data/clean/findings.json`;
none is typed by hand.

---

## 1. Czechia is the cheapest of its neighbours, and slightly above the EU average

At **16.36 EUR cents per kWh**, Czech mid-size industry pays less than any of its five
neighbouring markets:

| | EUR cents/kWh | vs Czechia |
|---|---:|---:|
| **Czechia** | **16.36** | — |
| Poland | 17.35 | +6.1% |
| Austria | 17.99 | +10.0% |
| Slovakia | 18.39 | +12.4% |
| Hungary | 18.76 | +14.7% |
| Germany | 19.22 | +17.5% |
| *EU average* | *15.96* | *−2.4%* |

The 14.9% gap to Germany is the number with commercial weight: a large share of Czech
industry is German-owned, and the same group can compare the electricity cost of its
Czech and German sites directly.

But Czechia sits **+2.5% above the EU average**. "Cheap energy" is a credible pitch when
the comparison is a neighbour, and not when the comparison is Europe. Anyone repeating
the first claim without the second will be corrected by a procurement manager who has
seen the Eurostat table.

## 2. Two thirds of the bill is the part a supplier controls

This is the finding with the most direct commercial consequence, and the one that
requires the careful data handling described in [METHOD.md](METHOD.md).

Composition of the 2025 industrial price, excluding VAT:

| | Energy & supply | Network | Taxes | Commodity share |
|---|---:|---:|---:|---:|
| **Czechia** | 11.02 | 3.85 | 1.79 | **66.1%** |
| Austria | 11.73 | 3.99 | 2.29 | 65.1% |
| Hungary | 12.34 | 4.87 | 1.84 | 64.8% |
| Slovakia | 11.49 | 4.09 | 2.53 | 63.4% |
| *EU average* | *10.21* | *3.36* | *2.76* | *62.5%* |
| Germany | 10.52 | 5.54 | 3.89 | 52.7% |
| Poland | 7.87 | 3.35 | 6.07 | 45.5% |

*EUR cents per kWh.*

Czechia has the **highest addressable share of the seven markets**. A supplier prices
energy and supply; network charges are set by the regulator and taxes by the state, and
they are identical whichever supplier the customer signs.

What that is worth, concretely. A 10% cut on the commodity:

| | Takes off the customer's total bill | Costs the supplier |
|---|---:|---:|
| **Czechia** | **6.6%** | 11.02 EUR/MWh |
| Austria | 6.5% | 11.73 EUR/MWh |
| Hungary | 6.5% | 12.34 EUR/MWh |
| Slovakia | 6.3% | 11.49 EUR/MWh |
| Germany | 5.3% | 10.52 EUR/MWh |
| Poland | 4.6% | 7.87 EUR/MWh |

The same discount does noticeably more work in Czechia than in Germany, and 43% more
than in Poland, where nearly half the bill is tax that no supplier can discount. Where a
commercial team chooses to compete on price, the Czech market rewards it more than any of
its neighbours.

The corollary is worth saying out loud: even in the best case here, a 10% commodity cut
moves the customer's total energy cost by 6.6%. If a customer's decision needs a
double-digit saving, price alone will not produce it in any of these markets.

## 3. Large consumers get a smaller size discount here — and it reverses

Price falls with consumption everywhere. How steeply differs a great deal.

Measured between the smallest band (<20 MWh) and the largest band **every** country
reports (70 000–149 999 MWh):

| | Size discount |
|---|---:|
| *EU average* | *−59.2%* |
| Poland | −58.3% |
| Germany | −55.8% |
| Austria | −50.6% |
| Slovakia | −49.4% |
| Hungary | −34.9% |
| **Czechia** | **−34.5%** |

Czechia has the flattest curve in the group. Small Czech businesses do relatively well;
large ones do not.

And the Czech curve does something no other market here does at that point: **it turns
back up**. Consumers in the 20 000–69 999 MWh band pay 16.4 cents — the same as the band
below them — and the 70 000–149 999 MWh band pays **18.8 cents**, more than a mid-size
factory.

Two cautions before reading anything into that. Czechia does not publish the ≥150 000 MWh
band at all, so the very largest consumers are invisible here. And a band with few
consumers in it produces a noisy average. The honest statement is: *in the data Eurostat
publishes, the Czech volume discount stops at 20 000 MWh*, and why is a question for
someone with contract-level data.

Either way, the commercially exposed segment is identified: large industrial accounts
that get less volume benefit than their EU peers, and that have the scale and the
sophistication to tender internationally.

## 4. Prices came down, but not all the way back

Czech industrial electricity, band ID:

| | EUR cents/kWh |
|---|---:|
| 2021-S2 (pre-crisis) | 9.92 |
| 2023-S1 (peak) | 18.32 |
| 2025-S2 (latest) | 16.36 |

Prices rose **84.7%** to the peak, have since fallen **10.7%**, and remain **+64.9%**
above pre-crisis. Anyone budgeting a return to 2021 levels is budgeting for something the
data gives no sign of.

Czechia's path through 2022–23 was also visibly shallower than its neighbours' — its peak
came later and lower relative to its own baseline. For a customer who was burned by
volatility rather than by level, that is the more persuasive argument, and it is
independent of price.

## 5. Gas points the same way

Industrial gas, 10 000–99 999 GJ band, 2025-S2:

| | EUR cents/kWh |
|---|---:|
| Hungary | 5.18 |
| **Czechia** | **5.68** |
| Slovakia | 6.40 |
| Austria | 6.41 |
| Poland | 6.47 |
| Germany | 7.13 |
| *EU average* | *6.05* |

Czech industrial gas is **6.1% below the EU average** and second cheapest of the six —
a better relative position than electricity, where Czechia is slightly above the EU line.
For a dual-fuel customer the combined position is stronger than the electricity figure
alone suggests.

---

## What would change these conclusions

- **A network tariff reform.** The commodity share is 66% today; a large network charge
  increase would cut the leverage of any price-led strategy without a single market price
  moving.
- **Czechia publishing the top band.** Conclusion 3 rests on the band below it.
- **A change in the industrial mix.** Band averages reflect which companies sit in each
  band, so a large new consumer moves the average without any price changing.
- **The next semester.** The gap to the EU average is 2.5%, which is small enough that
  one release could close it. The 15% gap to Germany is not.

## Reproducing this

```bash
python run_analysis.py
```

Three seconds, offline, from the cached API responses in `data/raw/`. Every figure above
comes out of `data/clean/findings.json`; the workbook and the deck read the same file, so
the three cannot disagree.
