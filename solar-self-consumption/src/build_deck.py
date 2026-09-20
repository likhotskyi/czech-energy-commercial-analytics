"""
Step 5: fill the read-only template with the findings.

Every figure comes from data/clean/findings.json. Replacement happens run by run so
the template's fonts survive, and a chart placeholder's two stacked shapes are both
removed before the image goes in.

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
    head = f["headline"]
    grid = f["sizing"]["by_profile"]
    ratios = f["sizing"]["ratios"]
    base = f["base_case"]["by_profile"]
    largest = f["largest_viable_system"]["by_profile"]
    retail = f["retail_components_eur_per_kwh"]
    avoided = f["avoided_price_eur_per_kwh"]
    capture = f["capture_rate"]["by_year"]
    locations = f["by_location"]["results"]
    day = f["typical_june_day"]
    names = {p.key: p.name for p in profiles.PROFILES}

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    images = {
        "day": charts.typical_day(day["series"], names, CHART_DIR / "day.png"),
        "sizing": charts.self_consumption_curve(grid, names, ratios,
                                                CHART_DIR / "sizing.png"),
        "capture": charts.capture_rate(capture, CHART_DIR / "capture.png"),
        "locations": charts.by_location(locations, CHART_DIR / "locations.png"),
    }

    office_max = largest["office"]
    night_max = largest["night_heavy"]
    capture_years = head["capture_years"]
    sunniest = max(locations, key=lambda k: locations[k]["yield_kwh_per_kwp"])
    dullest = min(locations, key=lambda k: locations[k]["yield_kwh_per_kwp"])
    consumption = meta["annual_consumption_mwh"]
    base_ratio_key = f"{f['sizing']['base_ratio']:.2f}"
    profile_paybacks = [grid[k][base_ratio_key]["payback_years"]["commodity_and_taxes"]
                        for k in grid]
    profile_payback_spread = max(profile_paybacks) - min(profile_paybacks)

    values = {
        "DECK_TITLE": "Rooftop solar:\nwhich customers, and how big",
        "SUBTITLE": "The load profile does not decide whether a business should "
                    "install solar. It decides how large a system it can absorb "
                    "before the surplus stops paying for itself.",
        "SOURCE_LINE": f"Hourly generation: PVGIS (European Commission JRC), "
                       f"{meta['analysis_year']}. Wholesale prices: Fraunhofer ISE. "
                       f"Retail price: Eurostat.",
        "GENERATED": f"Generated {datetime.now():%d %B %Y}",
        "PERIOD": f"{meta['analysis_year']} hourly, {consumption:,} MWh/year site",

        "S2_TITLE": "A kilowatt-hour used on site is worth three sold",
        "S2_LEDE": f"A {consumption:,} MWh/year site in {f['sizing']['location']}, "
                   f"roof-mounted system facing south.",
        "KPI1_LABEL": "SELF-CONSUMED vs EXPORTED kWh",
        "KPI1_VALUE": f"{head['retail_vs_export_ratio']:.1f}x",
        "KPI1_NOTE": f"{avoided['commodity_and_taxes']:.3f} EUR/kWh avoided against "
                     f"{base['office']['export_price_eur_per_kwh']:.3f} earned",
        "KPI2_LABEL": f"PROFILE SPREAD AT A {head['small_system_ratio']:.0%} SYSTEM",
        "KPI2_VALUE": f"{head['spread_at_small_pp']:.0f} pts",
        "KPI2_NOTE": "at this size the profile barely matters",
        "KPI3_LABEL": f"AT A {head['large_system_ratio']:.0%} SYSTEM",
        "KPI3_VALUE": f"{head['spread_at_large_pp']:.0f} pts",
        "KPI3_NOTE": "at this size it decides the project",
        "KPI4_LABEL": "SYSTEM SIZE THAT STILL PAYS BACK",
        "KPI4_VALUE": f"{head['size_ratio_best_to_worst']:.1f}x",
        "KPI4_NOTE": f"{office_max['max_kwp']:,.0f} kWp for a daytime customer "
                     f"against {night_max['max_kwp']:,.0f} kWp for a night one",
        "S2_FINDING":
            f"A kilowatt-hour the site consumes itself replaces one it would have "
            f"bought at {avoided['commodity_and_taxes']:.3f} EUR/kWh. A kilowatt-hour "
            f"it exports earns {base['office']['export_price_eur_per_kwh']:.3f} — solar "
            f"generates exactly when wholesale prices are lowest. So the share the "
            f"site consumes itself decides the investment.\n\n"
            f"That share depends on when the business runs, not on the roof. Which makes "
            f"it a sales question: the customer's own metering answers it before "
            f"anyone visits the site.",

        "S3_TITLE": "One June day, two customers, the same system",
        "S3_LEDE": f"An average June weekday: a {day['kwp']:,.0f} kWp system against "
                   f"two customers with identical annual consumption.",
        "S3_TAKEAWAY":
            f"The daytime customer's load sits above the generation curve all day, so "
            f"nothing is exported and every kilowatt-hour is worth the full retail "
            f"price.\n\n"
            f"The night-heavy customer draws "
            f"{day['series']['night_heavy']['12']:,.0f} kW at noon against "
            f"{day['series']['generation_kw']['12']:,.0f} kW of generation. The "
            f"difference leaves the site at the wholesale price — or at nothing, when "
            f"that price is negative.",

        "S4_TITLE": "The profile sets the size, not whether to build",
        "S4_LEDE": "Share of generation consumed on site, as the system grows.",
        "S4_TAKEAWAY":
            f"At a system covering {head['small_system_ratio']:.0%} of consumption "
            f"every profile absorbs almost everything — only "
            f"{head['spread_at_small_pp']:.0f} points separate them.\n\n"
            f"At {head['large_system_ratio']:.0%} the gap is "
            f"{head['spread_at_large_pp']:.0f} points: "
            f"{head['best_self_consumption_pct']:.0f}% against "
            f"{head['worst_self_consumption_pct']:.0f}%.\n\n"
            f"So the qualifying question is how many kilowatt-peak this particular "
            f"customer can absorb. Whether to offer solar at all is rarely the "
            f"interesting part.",

        "S5_TITLE": "The exported half is worth less every year",
        "S5_LEDE": "The price solar earns on the wholesale market, against the flat "
                   "baseload price of the same year.",
        "S5_TAKEAWAY":
            f"Solar earned {capture[str(capture_years[0])]['capture_rate']:.2f} of the "
            f"baseload price in {capture_years[0]} and "
            f"{capture[str(capture_years[1])]['capture_rate']:.2f} in "
            f"{capture_years[1]}.\n\n"
            f"More solar on the system depresses the price in exactly the hours solar "
            f"generates. Every year the half of the output that leaves the site is "
            f"worth less, and the half that stays matters more.",

        "S6_TITLE": "Where in Czechia barely matters",
        "S6_LEDE": f"Same daytime profile, same system size, five Czech locations.",
        "S6_TAKEAWAY":
            f"{sunniest} yields "
            f"{locations[sunniest]['yield_kwh_per_kwp']:,.0f} kWh/kWp against "
            f"{locations[dullest]['yield_kwh_per_kwp']:,.0f} in {dullest} — "
            f"{(locations[sunniest]['yield_kwh_per_kwp'] / locations[dullest]['yield_kwh_per_kwp'] - 1) * 100:.0f}% "
            f"across the whole country, worth "
            f"{locations[dullest]['payback_years_at_1000'] - locations[sunniest]['payback_years_at_1000']:.1f} "
            f"years of payback.\n\n"
            f"At a fixed system size the customer's shape moves payback by a similar "
            f"amount ({profile_payback_spread:.1f} years). The difference is that "
            f"geography does not change how large a system the site can absorb, and "
            f"the profile does — by {head['size_ratio_best_to_worst']:.1f}x.\n\n"
            f"So region is a tie-breaker. Operating hours decide the project.",

        "S7_TITLE": "What this changes for who we approach",
        "S7_LEDE": "Three things follow for how solar is sold to business customers.",
        "COL1_NUM": "01",
        "COL1_HEAD": "Qualify on operating hours before roof area",
        "COL1_BODY": f"Two customers with the same consumption and the same roof "
                     f"support systems {head['size_ratio_best_to_worst']:.1f}x apart "
                     f"within the same payback. Operating hours are already in the "
                     f"CRM, or one question away. Payback alone would not separate "
                     f"these customers; the size they can absorb does.",
        "COL2_NUM": "02",
        "COL2_HEAD": "Sell the size the customer can absorb",
        "COL2_BODY": f"Oversizing does not fail loudly. It quietly converts "
                     f"{avoided['commodity_and_taxes']:.3f} EUR/kWh of avoided cost "
                     f"into {base['office']['export_price_eur_per_kwh']:.3f} EUR/kWh of "
                     f"export revenue. The right answer is the largest system that "
                     f"still lands inside the customer's own payback hurdle.",
        "COL3_NUM": "03",
        "COL3_HEAD": "For the wrong shape, sell something that moves the load",
        "COL3_BODY": f"A night-heavy site does not become a good solar customer by "
                     f"buying fewer panels. It becomes one by shifting load into the "
                     f"day, or by storing it. Different product, and this analysis "
                     f"says which customers need it.",

        "S8_TITLE": "How the numbers were made, and where they stop",
        "S8_LEDE": "Every figure is computed from the cached responses in this "
                   "repository and can be reproduced with one command.",
        "DQ1_LABEL": "HOURLY PERIODS MODELLED",
        "DQ1_VALUE": f"{8760 * len(locations):,}",
        "DQ1_NOTE": f"{len(locations)} locations x a full year, hour by hour",
        "DQ2_LABEL": "RETAIL PRICE AVOIDED",
        "DQ2_VALUE": f"{avoided['commodity_and_taxes']:.3f}",
        "DQ2_NOTE": f"EUR/kWh: energy {retail['energy_supply']:.3f} plus taxes "
                    f"{retail['taxes_excl_vat']:.3f}",
        "DQ3_LABEL": "PAYBACK SPAN ACROSS THE CAPEX RANGE",
        "DQ3_VALUE": f"{min(base['office']['payback_by_capex']['commodity_and_taxes'].values()):.1f}"
                     f"-{max(base['office']['payback_by_capex']['commodity_and_taxes'].values()):.1f}",
        "DQ3_NOTE": "years, at 700 to 1 300 EUR/kWp",
        "METHOD_LEFT": bullets([
            "Self-consumption is computed hour by hour as min(generation, load). "
            "Netting over a month would let August sunshine cancel a February night.",
            "PVGIS timestamps are UTC. That was verified, not assumed: June output "
            "peaks at the hour solar noon falls for that longitude.",
            "Generation and prices are joined on the UTC hour, so the clock change "
            "cannot silently drop an hour.",
            "Network charges are partly capacity-based and do not fall when "
            "consumption does, so the model runs three avoided-cost scenarios and "
            "reports all three.",
        ]),
        "METHOD_RIGHT": bullets([
            "Stylised load profiles, not metered customer data. A real site has "
            "shutdowns, seasonality and production peaks.",
            "Simple payback, undiscounted, before any subsidy, grant or tax "
            "treatment. The ranking between customers is the durable result; the "
            "absolute years move with the quote.",
            "Generation is from 2023, the most recent year PVGIS publishes hourly. "
            "The solar resource varies about 5% year to year.",
            "City-centre coordinates stand in for a site in that region. A real "
            "project uses the roof's own orientation, pitch and shading survey.",
        ]),
    }

    prs = Presentation(str(TEMPLATE))
    filled: set[str] = set()
    for slide in prs.slides:
        place_charts(slide, images)
        filled |= fill_tokens(slide, values)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "rooftop_solar_targeting.pptx"
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
