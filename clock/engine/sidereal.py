"""
clock.engine.sidereal
=====================
Star-based time systems that don't appear in the original time_check.py.

Julian Date (JD)
    Continuous count of days since Jan 1, 4713 BC noon (Julian calendar).
    Standard in astronomy. JD 2451545.0 = J2000.0 = 2000-01-01 12:00 UTC.

Holocene Era (HE)
    Gregorian year + 10,000. Puts all of recorded human history in
    positive numbers. HE 12026 = 2026 CE.

Greenwich Mean Sidereal Time (GMST)
    Earth's rotation angle referenced to distant stars (not the sun).
    Advances ~3m 56s faster than solar time per day. Used in astronomy
    and radio telescope pointing. Returned in decimal hours (0-24).

No external deps. Pure stdlib math.
"""

import math
from datetime import datetime, timezone
from ..engine.context import SiderealContext


def _julian_date(dt: datetime) -> float:
    """
    Compute Julian Date from a UTC datetime.
    Algorithm: Meeus, Astronomical Algorithms Ch. 7.
    """
    # Ensure we're working in UTC
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    y, m, d = dt.year, dt.month, dt.day
    # Fractional day including time
    day_frac = d + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24.0

    if m <= 2:
        y -= 1
        m += 12

    a = int(y / 100)
    b = 2 - a + int(a / 4)

    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day_frac + b - 1524.5
    return round(jd, 5)


def _gmst(jd: float) -> float:
    """
    Greenwich Mean Sidereal Time in decimal hours (0-24).
    IAU formula, accurate to < 1 second for dates near J2000.
    """
    t  = (jd - 2451545.0) / 36525.0   # Julian centuries from J2000.0
    # GMST at 0h UT in seconds
    gmst_sec = (
        24110.54841
        + 8640184.812866 * t
        + 0.093104 * t**2
        - 6.2e-6   * t**3
    )
    # Add the Earth rotation for the current UT fraction of the day
    ut_frac  = (jd - int(jd) - 0.5) * 86400.0   # seconds into current UT day
    gmst_sec += ut_frac * 1.00273790935          # sidereal rate correction

    gmst_hours = (gmst_sec / 3600.0) % 24.0
    return round(gmst_hours, 4)


def compute(dt: datetime) -> SiderealContext:
    # Normalize to UTC for JD calculation
    if dt.tzinfo is None:
        dt_utc = dt
    else:
        dt_utc = dt.astimezone(timezone.utc)

    jd   = _julian_date(dt_utc)
    gmst = _gmst(jd)

    return SiderealContext(
        julian_date         = jd,
        holocene_year       = dt.year + 10000,
        sidereal_time_hours = gmst,
    )
