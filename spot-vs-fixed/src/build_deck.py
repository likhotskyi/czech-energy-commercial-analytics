"""
Step 5: fill the read-only template with the findings.

Every figure comes from data/clean/findings.json. Nothing is typed by hand, so the
deck cannot drift out of step with the workbook or the written report.

Two mechanics, both of which are how template automation usually breaks:
  * replacement happens run by run, never by assigning to a paragraph's text --
    that collapses the paragraph into one unstyled run and destroys the template's
    fonts and colours;
  * a chart placeholder is two stacked shapes (the box and its label) and both
    have to go, or the box shows as grey strips either side of the chart.

    python src/build_deck.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

import charts
import profiles

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
TEMPLATE = ROOT / "templates" / "report_template.pptx"
OUT_DIR = ROOT / "output"
CHART_DIR = OUT_DIR / "charts"

TOKEN_RE = re.compile(r"\{\{([A-Z0-9_:]+)\}\}")


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
    f = json.loads((CLEAN / "findings.json").read_text(encoding="utf-8"))
    meta = f["meta"]
    inv = f["inversion"]
    first, last = inv["first_year"], inv["last_year"]
    factors = {k: {int(y): v for y, v in s.items()}
               for k, s in f["profile_factors"].items()}
    intraday = {int(y): b for y, b in f["intraday"].items()}
    volatility = {int(y): b for y, b in f["volatility"].items()}
    negative = {int(y): b for y, b in f["negative_prices"].items()}
    spread = f["customer_spread"]["by_year"][str(last)]
    seasonal = f["seasonality"]["by_profile"]
    names = {p.key: p.name for p in profiles.PROFILES}

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    images = {
        "intraday": charts.intraday_shape(
            {y: {int(h): v for h, v in b["index_to_baseload"].items()}
             for y, b in intraday.items()}, CHART_DIR / "intraday.png"),
        "factors": charts.profile_factors(factors, names, CHART_DIR / "factors.png"),
        "spread": charts.daily_spread(volatility, CHART_DIR / "spread.png"),
        "negative": charts.negative_by_hour(
            {int(h): v for h, v in negative[last]["hours_by_hour_of_day"].items()},
            last, negative[last]["hours"], CHART_DIR / "negative.png"),
    }

    naive_office = f["profile_factors_without_base_load"]["office"]
    volume = f["customer_spread"]["example_volume_mwh"]

    values = {
        "DECK_TITLE": "Spot or fixed?\nThe answer changed",
        "SUBTITLE": "What a business customer's own consumption shape does to the "
                    "price it pays on the Czech day-ahead market — and why the "
                    "recommendation for a daytime customer has reversed since 2021.",
        "SOURCE_LINE": f"Source: {meta['source']}, licence {meta['licence']}. "
                       f"{meta['settlement_periods']:,} settlement periods, "
                       f"{first}-{last}, Czech local time.",
        "GENERATED": f"Generated {datetime.now():%d %B %Y}",
        "PERIOD": f"{first}-{last}",

        "S2_TITLE": "The cheap customer and the expensive one swapped places",
        "S2_LEDE": "Profile factor: what a customer's shape does to its average "
                   "price, against a flat 24/7 load = 1.00.",
        "KPI1_LABEL": f"DAYTIME OFFICE PROFILE, {first}",
        "KPI1_VALUE": f"{inv['office_first_year']:.2f}",
        "KPI1_NOTE": f"paid {(inv['office_first_year'] - 1) * 100:.0f}% above the "
                     f"market average",
        "KPI2_LABEL": f"THE SAME PROFILE, {last}",
        "KPI2_VALUE": f"{inv['office_latest_year']:.2f}",
        "KPI2_NOTE": f"now {abs(inv['office_latest_year'] - 1) * 100:.0f}% below it — "
                     f"a {abs(inv['office_swing_pp']):.0f} point swing",
        "KPI3_LABEL": f"NIGHT-HEAVY PROFILE, {first} → {last}",
        "KPI3_VALUE": f"{inv['night_first_year']:.2f} → {inv['night_latest_year']:.2f}",
        "KPI3_NOTE": "the cheap shape became the expensive one",
        "KPI4_LABEL": f"WORTH, AT {volume:,} MWh A YEAR",
        "KPI4_VALUE": f"{spread['spread_eur_per_year_at_example_volume'] / 1000:,.0f}k",
        "KPI4_NOTE": f"EUR a year between the best and worst shape in {last}",
        "S2_FINDING":
            f"Two customers can buy the same volume, from the same supplier, in the "
            f"same year, on the same spot contract — and pay "
            f"{spread['spread_eur_per_mwh']:.1f} EUR/MWh differently. The only "
            f"difference is when they consume.\n\n"
            f"That was always true. What changed is the sign. In {first} the "
            f"night-heavy customer had the cheap shape, "
            f"{abs(inv['gap_first_year_pp']):.0f} points below the daytime one. In "
            f"{last} it is {abs(inv['gap_latest_year_pp']):.0f} points above. "
            f"A sales playbook written before 2023 now recommends the wrong product "
            f"to both of them.",

        "S3_TITLE": "Midday stopped being expensive",
        "S3_LEDE": f"Average price by hour of day, each year indexed to its own "
                   f"baseload so the shape can be compared across years.",
        "S3_TAKEAWAY":
            f"In {first} midday cost "
            f"{intraday[first]['midday_vs_night_pct']:+.0f}% against the small hours. "
            f"In {last} it is "
            f"{intraday[last]['midday_vs_night_pct']:+.0f}%.\n\n"
            f"The cheapest hour of the day is now "
            f"{intraday[last]['cheapest_hour']:02d}:00; in {first} it was "
            f"{intraday[first]['cheapest_hour']:02d}:00.\n\n"
            f"The expensive hours moved to the evening peak, "
            f"{intraday[last]['most_expensive_hour']:02d}:00, when solar output has "
            f"gone and demand has not.",

        "S4_TITLE": "Who the market rewards now, and who it used to",
        "S4_LEDE": "Profile factor by year. Above 1.00 the shape costs the customer "
                   "money; below 1.00 it earns them money.",
        "S4_TAKEAWAY":
            f"The daytime office profile crossed below the market average in "
            f"{inv['office_crosses_below_baseload_in']}. The night-heavy profile "
            f"crossed above it in {inv['night_crosses_above_baseload_in']}.\n\n"
            f"A continuous 24/7 load sits at 1.00 by definition. It is the benchmark "
            f"everything else is measured against.\n\n"
            f"The annual figure hides a season. In {last} the office profile is "
            f"{seasonal['office']['summer']:.2f} across the summer and "
            f"{seasonal['office']['winter']:.2f} across the winter: the advantage "
            f"is a solar advantage, and it reverses when the sun does.",

        "S5_TITLE": "The gap inside a single day keeps widening",
        "S5_LEDE": "Average spread between the highest and lowest price within a "
                   "single day.",
        "S5_TAKEAWAY":
            f"The gap between the cheapest and dearest moment of an average day went "
            f"from {volatility[first]['mean_daily_spread']:.0f} EUR/MWh in {first} to "
            f"{volatility[last]['mean_daily_spread']:.0f} in {last}.\n\n"
            f"That is the shape effect getting stronger, independently of the price "
            f"level: {first} and {last} had similar averages "
            f"({volatility[first]['mean']:.0f} against "
            f"{volatility[last]['mean']:.0f} EUR/MWh).\n\n"
            f"The worst single day in {last} spanned "
            f"{volatility[last]['worst_day_spread']:.0f} EUR/MWh.",

        "S6_TITLE": "Negative prices happen at midday now",
        "S6_LEDE": f"Hours of negative day-ahead prices in {last}, by hour of day.",
        "S6_TAKEAWAY":
            f"{negative[last]['hours']:.0f} hours of negative prices so far in "
            f"{last} ({negative[last]['share_of_year_pct']:.1f}% of the period), "
            f"against {negative[first]['hours']:.0f} hours in {first}.\n\n"
            f"The lowest settlement price recorded in {last} was "
            f"{negative[last]['lowest_price']:.0f} EUR/MWh.\n\n"
            f"A customer able to move load into these hours is paid to consume. There is "
            f"a product in that for anyone with flexible demand.",

        "S7_TITLE": "What this changes for how we sell",
        "S7_LEDE": "Three things follow for how a supplier sells to business customers.",
        "COL1_NUM": "01",
        "COL1_HEAD": "Price the shape, not just the volume",
        "COL1_BODY": f"Two customers with identical annual volume are worth "
                     f"{spread['spread_eur_per_year_at_example_volume']:,.0f} EUR a "
                     f"year apart at {volume:,} MWh. A fixed-price offer quoted off "
                     f"the baseload for both mis-prices both: too dear for the "
                     f"daytime customer, too cheap for the night one.",
        "COL2_NUM": "02",
        "COL2_HEAD": "The daytime customer is the one to approach about spot",
        "COL2_BODY": f"Single-shift and office-hours loads now sit below the market "
                     f"average and are still moving. But the gain is seasonal — "
                     f"{seasonal['office']['summer']:.2f} in summer against "
                     f"{seasonal['office']['winter']:.2f} in winter — so the honest "
                     f"product is a seasonal or hybrid one. A flat promise is the kind of thing "
                     f"a customer resents every January.",
        "COL3_NUM": "03",
        "COL3_HEAD": "Certainty is worth more than it was",
        "COL3_BODY": f"The average day now spans "
                     f"{volatility[last]['mean_daily_spread']:.0f} EUR/MWh against "
                     f"{volatility[first]['mean_daily_spread']:.0f} in {first}. For a "
                     f"customer who cannot move load, that is the case for a fixed "
                     f"product — and the risk premium is easier to justify.",

        "S8_TITLE": "How the numbers were made, and where they stop",
        "S8_LEDE": "Every figure is computed from the cached price downloads in this "
                   "repository and can be reproduced with one command.",
        "DQ1_LABEL": "SETTLEMENT PERIODS",
        "DQ1_VALUE": f"{meta['settlement_periods']:,}",
        "DQ1_NOTE": f"Czech day-ahead prices, {first}-{last}",
        "DQ2_LABEL": "COMPLETE YEARS",
        "DQ2_VALUE": f"{len(meta['years_complete'])}",
        "DQ2_NOTE": "checked hour by hour against the calendar",
        "DQ3_LABEL": "IF THE BASE LOAD IS IGNORED",
        "DQ3_VALUE": f"{naive_office[str(last)]:.2f}",
        "DQ3_NOTE": f"the office factor instead of "
                    f"{factors['office'][last]:.2f} — same direction, twice the size",
        "METHOD_LEFT": bullets([
            "Prices are converted from UTC to Czech local time, so shifts and "
            "nights line up with when a factory actually runs.",
            "The market moved from hourly to 15-minute settlement on 1 October "
            "2025; every average here is weighted by period length.",
            "Load profiles keep a realistic base load overnight rather than "
            "dropping to zero, which halves the measured effect.",
            "Delivered hours were checked against the calendar year, so a missing "
            "day could not pass as a complete year.",
        ]),
        "METHOD_RIGHT": bullets([
            "The profile factor isolates the shape effect. A real fixed offer also "
            "contains a forward price, a risk premium and balancing costs, none of "
            "which are public.",
            "These are stylised profiles rather than metered customer data. A real "
            "site has seasonality, shutdowns and production peaks.",
            "Past shapes are history. They show where the market has moved; where it "
            "goes by the end of a three-year contract is another question.",
            "Seasonal factors are computed against each season's own baseload, so what "
            "they measure is shape. The fact that winter power costs more is "
            "already divided out.",
            f"{last} covers January to August only and is labelled as such "
            f"throughout.",
        ]),
    }

    prs = Presentation(str(TEMPLATE))
    filled: set[str] = set()
    for slide in prs.slides:
        place_charts(slide, images)
        filled |= fill_tokens(slide, values)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "spot_vs_fixed_czech_market.pptx"
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
