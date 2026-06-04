"""
clock.engine.wheel
==================
Wheel of the Year -- 8 sabbats for any year.

Solstices and equinoxes: computed via Jean Meeus algorithm
(Astronomical Algorithms, Ch. 27). Accurate to ~1 minute.

Cross-quarters (Imbolc, Beltane, Lughnasadh, Samhain): traditional
fixed dates (Feb 2, May 1, Aug 1, Oct 31). These are calendar dates
by convention, not astronomical events.

No external deps. Pure stdlib math.
"""

import math
from datetime import datetime, timedelta
from ..engine.context import WheelContext


# ---------------------------------------------------------------------------
# Meeus algorithm for equinoxes and solstices
# Reference: Astronomical Algorithms, Jean Meeus, 2nd ed., Ch. 27
# ---------------------------------------------------------------------------

def _jde_to_datetime(jde: float) -> datetime:
    """Convert Julian Day Ephemeris to a UTC datetime."""
    # Julian Day 0 = Jan 1, 4713 BC noon
    # J2000.0 = JDE 2451545.0 = 2000-01-01 12:00 TT (approx = UTC for our purposes)
    j2000 = jde - 2451545.0
    return datetime(2000, 1, 1, 12, 0) + timedelta(days=j2000)


def _meeus_event(year: int, event: str) -> datetime:
    """
    Compute approximate datetime of a solstice or equinox for a given year.
    event: 'spring' | 'summer' | 'fall' | 'winter'
    """
    # Table 27.a from Meeus -- JDE0 mean value for each event
    y = (year - 2000) / 1000.0

    if event == "spring":
        jde0 = (2451623.80984
                + 365242.37404 * y
                + 0.05169 * y**2
                - 0.00411 * y**3
                - 0.00057 * y**4)
    elif event == "summer":
        jde0 = (2451716.56767
                + 365241.62603 * y
                + 0.00325 * y**2
                + 0.00888 * y**3
                - 0.00030 * y**4)
    elif event == "fall":
        jde0 = (2451810.21715
                + 365242.01767 * y
                - 0.11575 * y**2
                + 0.00337 * y**3
                + 0.00078 * y**4)
    elif event == "winter":
        jde0 = (2451900.05952
                + 365242.74049 * y
                - 0.06223 * y**2
                - 0.00823 * y**3
                + 0.00032 * y**4)
    else:
        raise ValueError(f"Unknown event: {event}")

    # Correction terms (Table 27.b) -- accounts for planetary perturbations
    t = (jde0 - 2451545.0) / 36525.0

    w  = 35999.373 * t - 2.47
    dl = 1 + 0.0334 * math.cos(math.radians(w)) + 0.0007 * math.cos(math.radians(2 * w))

    # Sum of periodic terms (abbreviated -- 25 largest terms from Meeus Table 27.c)
    s = (
        485 * math.cos(math.radians(324.96 +   1934.136 * t))
      + 203 * math.cos(math.radians(337.23 +  32964.467 * t))
      + 199 * math.cos(math.radians(342.08 +     20.186 * t))
      + 182 * math.cos(math.radians( 27.85 + 445267.112 * t))
      + 156 * math.cos(math.radians( 73.14 +  45036.886 * t))
      + 136 * math.cos(math.radians(171.52 +  22518.443 * t))
      +  77 * math.cos(math.radians(222.54 +  65928.934 * t))
      +  74 * math.cos(math.radians(296.72 +   3034.906 * t))
      +  70 * math.cos(math.radians(243.58 +   9037.513 * t))
      +  58 * math.cos(math.radians(119.81 +  33718.147 * t))
      +  52 * math.cos(math.radians(297.17 +    150.678 * t))
      +  50 * math.cos(math.radians( 21.02 +   2281.226 * t))
      +  45 * math.cos(math.radians(247.54 +  29929.562 * t))
      +  44 * math.cos(math.radians(325.15 +  31555.956 * t))
      +  29 * math.cos(math.radians( 60.93 +   4443.417 * t))
      +  18 * math.cos(math.radians(155.12 +  67555.328 * t))
      +  17 * math.cos(math.radians(288.79 +   4562.452 * t))
      +  16 * math.cos(math.radians(198.04 +  62894.029 * t))
      +  14 * math.cos(math.radians(199.76 +  31557.381 * t))
      +  12 * math.cos(math.radians( 95.39 +  14577.848 * t))
      +  10 * math.cos(math.radians(287.11 +  31555.931 * t))
      +  10 * math.cos(math.radians(320.81 +  34777.259 * t))
      +   6 * math.cos(math.radians(124.13 +  31555.149 * t))
      +   5 * math.cos(math.radians(303.26 +    628.308 * t))
    )

    jde = jde0 + (0.00325 * s) / dl
    return _jde_to_datetime(jde)


# ---------------------------------------------------------------------------
# Build sabbat ladder for a year
# ---------------------------------------------------------------------------

def _sabbats_for_year(year: int) -> list[tuple[str, datetime, str]]:
    """Return all 8 sabbats for the given year, sorted by date."""
    cross_quarters = [
        ("Imbolc",     datetime(year,  2,  2), "cross-quarter"),
        ("Beltane",    datetime(year,  5,  1), "cross-quarter"),
        ("Lughnasadh", datetime(year,  8,  1), "cross-quarter"),
        ("Samhain",    datetime(year, 10, 31), "cross-quarter"),
    ]
    astronomical = [
        ("Ostara", _meeus_event(year, "spring"), "equinox"),
        ("Litha",  _meeus_event(year, "summer"), "solstice"),
        ("Mabon",  _meeus_event(year, "fall"),   "equinox"),
        ("Yule",   _meeus_event(year, "winter"), "solstice"),
    ]
    all_sabbats = cross_quarters + astronomical
    all_sabbats.sort(key=lambda x: x[1])
    return all_sabbats


# ---------------------------------------------------------------------------
# Public compute function
# ---------------------------------------------------------------------------

def compute(dt: datetime) -> WheelContext:
    # Build the ladder. If we're in late December, we also need next year's
    # early sabbats to correctly identify "next" after Yule.
    sabbats = _sabbats_for_year(dt.year)

    # Strip time and tz from dt for date comparison (sabbats are date-level events)
    today = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    past   = [(n, d, t) for n, d, t in sabbats if d <= today]
    future = [(n, d, t) for n, d, t in sabbats if d >  today]

    # If no future sabbat in this year (past Yule), pull from next year
    if not future:
        next_year = _sabbats_for_year(dt.year + 1)
        future = next_year

    last = max(past, key=lambda x: x[1]) if past else None
    nxt  = min(future, key=lambda x: x[1])

    # If no past sabbat yet this year (before Imbolc), pull from previous year
    if last is None:
        prev_year = _sabbats_for_year(dt.year - 1)
        last = max(prev_year, key=lambda x: x[1])

    ls_name, ls_date, ls_type = last
    ns_name, ns_date, ns_type = nxt

    return WheelContext(
        last_sabbat_name      = ls_name,
        last_sabbat_date      = ls_date,
        last_sabbat_type      = ls_type,
        last_sabbat_days_ago  = (today - ls_date).days,
        next_sabbat_name      = ns_name,
        next_sabbat_date      = ns_date,
        next_sabbat_type      = ns_type,
        next_sabbat_days_away = (ns_date - today).days,
        ladder                = sabbats,
    )
