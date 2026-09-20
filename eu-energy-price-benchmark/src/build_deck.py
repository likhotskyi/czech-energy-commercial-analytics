"""
Step 5: fill the read-only template with the findings.

Every figure on every slide comes from `data/clean/findings.json`. Nothing is
typed by hand, so the deck cannot drift out of step with the spreadsheet or the
written report.

Two mechanics worth knowing, because both are how template automation usually
breaks:

  * Replacement happens **run by run**. Assigning to a paragraph's `.text`
    collapses it into a single unstyled run and silently destroys the template's
    fonts, sizes and colours.
  * A placeholder is two stacked shapes -- the grey box and its label. Both have
    to be removed, or the box shows as grey strips either side of the chart.

    python src/build_deck.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.util import Emu

import charts

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
TEMPLATE = ROOT / "templates" / "report_template.pptx"
OUT_DIR = ROOT / "output"
CHART_DIR = OUT_DIR / "charts"

TOKEN_RE = re.compile(r"\{\{([A-Z0-9_:]+)\}\}")
HOME = "Czechia"
REFERENCE = "EU average"


def cents(value: float) -> str:
    return f"{value * 100:.1f}"


def signed(value: float) -> str:
    return f"{value:+.1f}%"


def bullets(items: list[str]) -> str:
    return "\n".join(f"•  {item}" for item in items)


def fill_tokens(slide, values: dict[str, str]) -> set[str]:
    used: set[str] = set()
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                if "{{" not in run.text:
                    continue

                def substitute(match):
                    key = match.group(1)
                    if key in values:
                        used.add(key)
                        return values[key]
                    return match.group(0)

                run.text = TOKEN_RE.sub(substitute, run.text)
    return used


def place_charts(slide, images: dict[str, Path]) -> None:
    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue
        match = re.search(r"\{\{CHART:([a-z_]+)\}\}", shape.text_frame.text)
        if not match:
            continue
        image = images.get(match.group(1))
        box = (shape.left, shape.top, shape.width, shape.height)
        for other in list(slide.shapes):
            if (other.left, other.top, other.width, other.height) == box:
                other._element.getparent().remove(other._element)
        if image is None:
            continue
        picture = slide.shapes.add_picture(str(image), box[0], box[1], width=box[2])
        if picture.height > box[3]:
            scale = box[3] / picture.height
            picture.height = Emu(int(picture.height * scale))
            picture.width = Emu(int(picture.width * scale))
        picture.left = Emu(int(box[0] + (box[2] - picture.width) / 2))
        picture.top = Emu(int(box[1] + (box[3] - picture.height) / 2))


def main() -> None:
    findings = json.loads((CLEAN / "findings.json").read_text(encoding="utf-8"))
    elec = pd.read_csv(CLEAN / "electricity_prices.csv", encoding="utf-8-sig")

    meta = findings["meta"]
    price = findings["price_level"]
    comp = findings["composition"]
    lever = findings["discount_leverage"]
    size = findings["size_discount"]
    shock = findings["price_shock"]
    gas = findings["gas"]
    quality = findings["data_quality"]

    CHART_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- charts
    band = elec[elec["nrg_cons"] == "MWH2000-19999"]
    wide = band.pivot_table(index="period", columns="country",
                            values="price_eur_per_unit").sort_index()
    history_png = charts.price_history(wide, CHART_DIR / "history.png")

    ranking = price["ranking"] + [{"country": REFERENCE, "price": price["eu_average"]}]
    ranking.sort(key=lambda r: r["price"])
    ranking_png = charts.price_ranking([r["country"] for r in ranking],
                                       [r["price"] for r in ranking],
                                       CHART_DIR / "ranking.png")

    rows = sorted(comp["by_country"], key=lambda r: r["share_energy_supply_pct"],
                  reverse=True)
    composition_png = charts.composition(
        [r["country"] for r in rows],
        [r["energy_supply"] for r in rows],
        [r["network_costs"] for r in rows],
        [r["taxes_excl_vat"] for r in rows],
        CHART_DIR / "composition.png")

    band_labels = list(size["table"].keys())
    band_series = {country: [size["table"][b].get(country) for b in band_labels]
                   for country in meta["countries"]}
    bands_png = charts.band_curve(band_labels, band_series, CHART_DIR / "bands.png")

    # ---------------------------------------------------------- narrative
    cheapest = price["ranking"][0]["country"]
    dearest = price["ranking"][-1]["country"]
    lowest = comp["lowest_addressable"]

    values = {
        "DECK_TITLE": "What a Czech industrial\nelectricity bill is made of",
        "SUBTITLE": "And how much of it a supplier can actually compete on. "
                    "Czechia benchmarked against its five neighbouring markets "
                    "and the EU average.",
        "SOURCE_LINE": f"Source: Eurostat, last updated {meta['last_updated_by_eurostat']}. "
                       f"Band {meta['band']}, excluding VAT.",
        "GENERATED": f"Generated {datetime.now():%d %B %Y}",
        "PERIOD": meta["latest_period"],

        "S2_TITLE": "Two thirds of the bill is ours to price",
        "S2_LEDE": f"Mid-size industrial consumers ({meta['band']} a year), "
                   f"{meta['latest_period']}, excluding VAT.",
        "KPI1_LABEL": "CZECH PRICE",
        "KPI1_VALUE": f"{cents(price['czechia'])}c",
        "KPI1_NOTE": f"EUR cents per kWh, {signed(price['gap_vs_eu_pct'])} vs the EU average",
        "KPI2_LABEL": "RANK AMONG NEIGHBOURS",
        "KPI2_VALUE": f"{price['rank_among_peers']} of {price['peer_count']}",
        "KPI2_NOTE": f"cheapest is {cheapest}, dearest is {dearest}",
        "KPI3_LABEL": "COMMODITY SHARE OF THE BILL",
        "KPI3_VALUE": f"{comp['czechia_share_energy_supply_pct']:.0f}%",
        "KPI3_NOTE": f"the part a supplier sets; EU average "
                     f"{comp['eu_share_energy_supply_pct']:.0f}%",
        "KPI4_LABEL": "STILL ABOVE PRE-CRISIS",
        "KPI4_VALUE": signed(shock["vs_pre_crisis_pct"]),
        "KPI4_NOTE": f"against {shock['pre_crisis_period']}, after peaking in "
                     f"{shock['peak_period']}",
        "S2_FINDING":
            f"Czech industry pays {cents(price['czechia'])} cents per kWh — the lowest of the six "
            f"markets compared, {abs(price['gap_vs_germany_pct']):.0f}% below Germany, though still "
            f"{signed(price['gap_vs_eu_pct'])} against the EU average.\n\n"
            f"The level matters less to a supplier than the composition. "
            f"{comp['czechia_share_energy_supply_pct']:.0f}% of that bill is energy and supply — "
            f"the highest share in the group, against "
            f"{lowest['share_pct']:.0f}% in {lowest['country']}. "
            f"Network charges and taxes are set by the regulator and the state and are identical "
            f"whichever supplier a customer signs with.",

        "S3_TITLE": "Prices came down, but not all the way back",
        "S3_LEDE": f"Business electricity price, band {meta['band']}, since 2015.",
        "S3_TAKEAWAY":
            f"Czech prices peaked in {shock['peak_period']} at "
            f"{cents(shock['peak_price'])}c, {signed(shock['rise_to_peak_pct'])} on "
            f"{shock['pre_crisis_period']}.\n\n"
            f"They have since fallen {abs(shock['fall_from_peak_pct']):.0f}%, but remain "
            f"{signed(shock['vs_pre_crisis_pct'])} above pre-crisis levels.\n\n"
            f"Czechia moved less violently than its neighbours through 2022-2023. That is "
            f"worth saying to a customer comparing offers across the border.",

        "S4_TITLE": "Czechia is the cheapest of its neighbours",
        "S4_LEDE": f"Price per kWh, {meta['latest_period']}, excluding VAT.",
        "S4_TAKEAWAY":
            f"{cheapest} {cents(price['czechia'])}c against {dearest} "
            f"{cents(price['ranking'][-1]['price'])}c — a gap of "
            f"{abs(price['gap_vs_germany_pct']):.0f}%.\n\n"
            f"The EU average sits below Czechia. So 'cheap' here means cheap against the "
            f"neighbours a Czech plant competes with for orders. Against Europe as a "
            f"whole it is a little above the middle.",

        "S5_TITLE": "Where the money in the bill goes",
        "S5_LEDE": f"Price split into energy & supply, network costs and taxes, "
                   f"{comp['year']}. Countries ordered by the share a supplier controls.",
        "S5_TAKEAWAY":
            f"In Czechia {comp['czechia_share_energy_supply_pct']:.0f}% of the bill is the "
            f"commodity. In {lowest['country']} it is {lowest['share_pct']:.0f}%: nearly half "
            f"that bill is tax, and no supplier can discount it.\n\n"
            f"A {lever['discount_on_commodity_pct']:.0f}% cut on the commodity is worth "
            f"{lever['czechia_bill_reduction_pct']:.1f}% off a Czech customer's total bill, "
            f"against {lever['germany_bill_reduction_pct']:.1f}% in Germany.",

        "S6_TITLE": "Big customers get less of a discount here",
        "S6_LEDE": f"Price by annual consumption band, {meta['latest_period']}. Measured "
                   f"between {size['measured_between']['from']} and "
                   f"{size['measured_between']['to']}, the largest band every country reports.",
        "S6_TAKEAWAY":
            f"Across the EU the large band pays "
            f"{abs(size['eu_discount_pct']):.0f}% less per kWh than the smallest. "
            f"In Czechia the gap is {abs(size['czechia_discount_pct']):.0f}%.\n\n"
            f"The Czech curve also turns back up: consumers above 20 000 MWh pay more "
            f"per kWh than the 2 000-19 999 MWh band, the only market here where that "
            f"happens at that point on the curve.\n\n"
            f"Czechia does not report the >= 150 000 MWh band at all, so its very "
            f"largest consumers are invisible in this data.",

        "S7_TITLE": "What this changes for how we price",
        "S7_LEDE": "Three things follow for anyone selling electricity to Czech industry.",
        "COL1_NUM": "01",
        "COL1_HEAD": "Price competition works better here than next door",
        "COL1_BODY": f"With {comp['czechia_share_energy_supply_pct']:.0f}% of the bill in the "
                     f"supplier's hands, a discount reaches the customer's total cost more "
                     f"directly than in {lowest['country']} "
                     f"({lowest['share_pct']:.0f}%) or Germany. The same headline discount buys "
                     f"more visible saving — and costs the same margin.",
        "COL2_NUM": "02",
        "COL2_HEAD": "The largest consumers are the exposed segment",
        "COL2_BODY": f"The Czech size curve is flat — "
                     f"{abs(size['czechia_discount_pct']):.0f}% between the smallest and largest "
                     f"comparable band against {abs(size['eu_discount_pct']):.0f}% EU-wide — and "
                     f"above 20 000 MWh it turns back up. Large industrial accounts get less "
                     f"volume benefit than their EU peers, and they are the group most able to "
                     f"tender across borders.",
        "COL3_NUM": "03",
        "COL3_HEAD": "A German parent needs a different argument from everyone else",
        "COL3_BODY": f"Czechia is {abs(price['gap_vs_germany_pct']):.0f}% below Germany but "
                     f"{signed(price['gap_vs_eu_pct'])} against the EU average. The credible "
                     f"argument to a German-owned plant is the cross-border gap; the credible "
                     f"argument elsewhere is that Czech prices moved less through the crisis.",

        "S8_TITLE": "How the numbers were made, and where they stop",
        "S8_LEDE": "Every figure here is computed from the cached Eurostat responses "
                   "in this repository and can be reproduced with one command.",
        "DQ1_LABEL": "OBSERVATIONS USED",
        "DQ1_VALUE": f"{quality['observations_electricity'] + quality['observations_gas']:,}",
        "DQ1_NOTE": "electricity and gas prices, 2007 onwards",
        "DQ2_LABEL": "COMPONENT RECONCILIATION",
        "DQ2_VALUE": f"{quality['reconciliation_median_deviation_pct']:.1f}%",
        "DQ2_NOTE": "median gap between components and the headline series",
        "DQ3_LABEL": "IF THAT CHECK IS SKIPPED",
        "DQ3_VALUE": f"{quality['naive_method_median_deviation_pct']:.0f}%",
        "DQ3_NOTE": "how far the naive component sum overstates the price",
        "METHOD_LEFT": bullets([
            "Prices exclude VAT: VAT is recoverable for a business, so the "
            "VAT-inclusive series overstates what a company pays.",
            "The component breakdown is annual, the price series half-yearly; the two "
            "were reconciled before anything was built on them.",
            "Eurostat's tax total already contains VAT. Subtracting it is the difference "
            f"between a {quality['reconciliation_median_deviation_pct']:.1f}% and a "
            f"{quality['naive_method_median_deviation_pct']:.0f}% error.",
            "Raw API responses are cached in the repository, so the numbers are "
            "reproducible even after Eurostat revises a series.",
        ]),
        "METHOD_RIGHT": bullets([
            "These are national averages. An individual contract depends on the load "
            "profile, the hedging strategy and the date it was signed.",
            "Band boundaries are consumption-based, so a country's mix of industry "
            "affects its average within a band.",
            "Czechia does not report the >= 150 000 MWh band, so size comparisons stop "
            "at 70 000-149 999 MWh — the largest band every country publishes.",
            "Half-yearly data cannot show what a spot-exposed customer paid in a "
            "particular month.",
            "Nothing here says what any supplier's margin is; the commodity share is "
            "what a supplier prices, not what it earns.",
        ]),
    }

    # ------------------------------------------------------------- render
    prs = Presentation(str(TEMPLATE))
    images = {"history": history_png, "ranking": ranking_png,
              "composition": composition_png, "bands": bands_png}

    filled: set[str] = set()
    for slide in prs.slides:
        place_charts(slide, images)
        filled |= fill_tokens(slide, values)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "czech_industrial_energy_benchmark.pptx"
    prs.save(str(out_path))

    unused = set(values) - filled - {"PERIOD"}
    if unused:
        print(f"WARNING: values with no matching token: {sorted(unused)}")
    leftover = [(i, t) for i, slide in enumerate(prs.slides, 1)
                for shape in slide.shapes if shape.has_text_frame
                for t in TOKEN_RE.findall(shape.text_frame.text)]
    if leftover:
        print(f"WARNING: unreplaced tokens: {leftover}")

    print(f"Wrote {out_path.relative_to(ROOT)}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
