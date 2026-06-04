"""
clock.engine.lunar
==================
Moon phase, cycle age, lunation anchors (prev/next new + full moon),
and folk moon names.

Reference point: Jan 6, 2000 18:14 UTC was a confirmed new moon.
Synodic period: 29.53058867 days.

No external deps. Pure stdlib math.
"""

import math
from datetime import datetime, timedelta
from ..engine.context import LunarContext

# Known new moon reference (J2000 epoch new moon)
_REF_NEW_MOON = datetime(2000, 1, 6, 18, 14)
_SYNODIC      = 29.53058867  # days

FULL_MOON_NAMES: dict[int, str] = {
    1:  "Wolf Moon",
    2:  "Snow Moon",
    3:  "Worm Moon",
    4:  "Pink Moon",
    5:  "Flower Moon",
    6:  "Strawberry Moon",
    7:  "Buck Moon",
    8:  "Sturgeon Moon",
    9:  "Harvest Moon",
    10: "Hunter's Moon",
    11: "Beaver Moon",
    12: "Cold Moon",
}


def _phase_name(age: float) -> str:
    if   age <  1.5:  return "New Moon"
    elif age <  7.4:  return "Waxing Crescent"
    elif age <  8.4:  return "First Quarter"
    elif age < 14.8:  return "Waxing Gibbous"
    elif age < 15.8:  return "Full Moon"
    elif age < 22.1:  return "Waning Gibbous"
    elif age < 23.1:  return "Last Quarter"
    elif age < 29.0:  return "Waning Crescent"
    else:             return "New Moon"


def _lunation_age(dt: datetime) -> tuple[float, float]:
    """Returns (age_days, cycle_pct)."""
    dt = dt.replace(tzinfo=None)  # normalize: reference point is naive UTC
    diff = (dt - _REF_NEW_MOON).total_seconds() / 86400.0
    age  = diff % _SYNODIC
    pct  = age / _SYNODIC * 100
    return age, pct


def _lunation_anchors(dt: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    """Returns (prev_new, next_new, prev_full, next_full)."""
    dt = dt.replace(tzinfo=None)  # normalize
    diff_days = (dt - _REF_NEW_MOON).total_seconds() / 86400.0
    n = math.floor(diff_days / _SYNODIC)

    prev_new = _REF_NEW_MOON + timedelta(days=_SYNODIC * n)
    next_new = _REF_NEW_MOON + timedelta(days=_SYNODIC * (n + 1))

    # Full moon is half a synodic period after new moon
    candidate_full = prev_new + timedelta(days=_SYNODIC / 2)
    if candidate_full > dt:
        next_full = candidate_full
        prev_full = next_full - timedelta(days=_SYNODIC)
    else:
        prev_full = candidate_full
        next_full = prev_full + timedelta(days=_SYNODIC)

    return prev_new, next_new, prev_full, next_full


def compute(dt: datetime) -> LunarContext:
    age, pct = _lunation_age(dt)
    prev_new, next_new, prev_full, next_full = _lunation_anchors(dt)

    return LunarContext(
        phase_name                = _phase_name(age),
        age_days                  = round(age, 1),
        cycle_pct                 = round(pct, 1),
        prev_new                  = prev_new,
        next_new                  = next_new,
        prev_full                 = prev_full,
        next_full                 = next_full,
        full_moon_name_this_month = FULL_MOON_NAMES.get(dt.month, ""),
        # Use the actual month the next full moon falls in, not current month
        full_moon_name_next       = FULL_MOON_NAMES.get(next_full.month, ""),
    )
