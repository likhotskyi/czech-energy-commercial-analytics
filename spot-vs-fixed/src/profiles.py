"""
Stylised load profiles for six recognisable kinds of business customer.

These are **not** measured customer data. They are deliberate simplifications, and
every number in them is stated here so a reader can disagree with a specific
assumption rather than with the whole exercise.

Two things make them more useful than a naive on/off shape:

  * **Nothing goes to zero.** A factory that runs one shift still has lighting,
    compressed air, ventilation, IT and standby losses overnight. Treating the
    off-shift as zero exaggerates every profile effect, and it is the single most
    common way a shape analysis overstates its own conclusion. Each profile below
    therefore has a base load expressed as a fraction of its operating load.

  * **Weekends are separate.** Most industrial sites drop to a maintenance level
    at the weekend, and weekend prices behave differently from weekday prices.

Hours are Czech local time (Europe/Prague) and refer to the hour a settlement
period starts: `range(6, 14)` means 06:00 up to but not including 14:00.

The output of a profile is a *relative weight* per settlement period. Only the
shape matters: the profile cost is a weighted average of price, so multiplying
every weight by a constant changes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LoadProfile:
    key: str
    name: str
    description: str
    operating_hours: range | tuple[range, ...]
    operating_days: str               # "weekdays" | "all"
    base_load: float                  # fraction of operating load, outside hours
    weekend_load: float               # fraction of operating load, whole weekend
    typical_customer: str

    def weights(self, hour: pd.Series, is_weekend: pd.Series) -> np.ndarray:
        ranges = (self.operating_hours if isinstance(self.operating_hours, tuple)
                  else (self.operating_hours,))
        in_hours = np.zeros(len(hour), dtype=bool)
        for r in ranges:
            in_hours |= hour.isin(list(r)).to_numpy()

        weights = np.full(len(hour), self.base_load, dtype=float)
        weights[in_hours] = 1.0

        if self.operating_days == "weekdays":
            weekend = is_weekend.to_numpy()
            weights[weekend] = self.weekend_load
        return weights


PROFILES: list[LoadProfile] = [
    LoadProfile(
        key="continuous",
        name="Continuous 24/7",
        description="Flat load every hour of every day.",
        operating_hours=range(0, 24),
        operating_days="all",
        base_load=1.0,
        weekend_load=1.0,
        typical_customer="Foundry, paper mill, cold store, data centre",
    ),
    LoadProfile(
        key="three_shift",
        name="Three shifts, Mon-Fri",
        description="Round the clock on weekdays, maintenance level at weekends.",
        operating_hours=range(0, 24),
        operating_days="weekdays",
        base_load=1.0,
        weekend_load=0.35,
        typical_customer="Automotive component plant, injection moulding",
    ),
    LoadProfile(
        key="two_shift",
        name="Two shifts, Mon-Fri 06:00-22:00",
        description="Two shifts on weekdays; 25% base load overnight.",
        operating_hours=range(6, 22),
        operating_days="weekdays",
        base_load=0.25,
        weekend_load=0.20,
        typical_customer="Machining, food processing, packaging",
    ),
    LoadProfile(
        key="single_shift",
        name="Single shift, Mon-Fri 06:00-14:00",
        description="One morning shift; 20% base load the rest of the time.",
        operating_hours=range(6, 14),
        operating_days="weekdays",
        base_load=0.20,
        weekend_load=0.15,
        typical_customer="Workshop, small manufacturer, print shop",
    ),
    LoadProfile(
        key="office",
        name="Office hours, Mon-Fri 08:00-18:00",
        description="Daytime occupancy; 15% base load out of hours.",
        operating_hours=range(8, 18),
        operating_days="weekdays",
        base_load=0.15,
        weekend_load=0.15,
        typical_customer="Office building, retail park, school, administration",
    ),
    LoadProfile(
        key="night_heavy",
        name="Night-heavy, daily 22:00-06:00",
        description="Load concentrated overnight, every day of the week; 45% by day.",
        operating_hours=(range(22, 24), range(0, 6)),
        operating_days="all",
        base_load=0.45,
        weekend_load=0.45,
        typical_customer="Cold storage pre-cooling, bakery, night-tariff heating",
    ),
]

BY_KEY = {p.key: p for p in PROFILES}


def profile_table() -> pd.DataFrame:
    """The assumptions, as a table, so they travel with the results."""
    rows = []
    for p in PROFILES:
        ranges = (p.operating_hours if isinstance(p.operating_hours, tuple)
                  else (p.operating_hours,))
        hours = ", ".join(f"{r.start:02d}:00-{r.stop % 24:02d}:00" for r in ranges)
        rows.append({
            "key": p.key,
            "profile": p.name,
            "operating_hours": hours,
            "operating_days": p.operating_days,
            "base_load_share": p.base_load,
            "weekend_load_share": p.weekend_load,
            "typical_customer": p.typical_customer,
        })
    return pd.DataFrame(rows)
