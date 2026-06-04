"""
clock.engine.solar_terms
========================
Chinese 24 solar terms (节气, Jieqi).

Each term marks the sun reaching a specific ecliptic longitude,
in 15° increments starting from 315° (Xiaohan, ~Jan 6).
The terms encode the agricultural and seasonal rhythm of the year
with more granularity than the Western 4-season model.

Algorithm: approximate sun longitude from day-of-year, binary search
for the day each term's longitude is crossed. Accurate to ~1-2 days.
For exact times, skyfield would be required.

No external deps. Pure stdlib math.
"""

import math
from datetime import datetime, timedelta
from ..engine.context import SolarTermContext


# ---------------------------------------------------------------------------
# 24 solar terms in order, with their ecliptic longitude (degrees)
# ---------------------------------------------------------------------------

_TERMS: list[tuple[str, float]] = [
    ("Xiaohan -- Minor Cold (小寒)",       285.0),
    ("Dahan -- Major Cold (大寒)",          300.0),
    ("Lichun -- Start of Spring (立春)",    315.0),
    ("Yushui -- Rain Water (雨水)",         330.0),
    ("Jingzhe -- Awakening of Insects (惊蛰)", 345.0),
    ("Chunfen -- Spring Equinox (春分)",      0.0),
    ("Qingming -- Clear and Bright (清明)",   15.0),
    ("Guyu -- Grain Rain (谷雨)",             30.0),
    ("Lixia -- Start of Summer (立夏)",       45.0),
    ("Xiaoman -- Grain Buds (小满)",          60.0),
    ("Mangzhong -- Grain in Ear (芒种)",      75.0),
    ("Xiazhi -- Summer Solstice (夏至)",      90.0),
    ("Xiaoshu -- Minor Heat (小暑)",         105.0),
    ("Dashu -- Major Heat (大暑)",           120.0),
    ("Liqiu -- Start of Autumn (立秋)",      135.0),
    ("Chushu -- End of Heat (处暑)",         150.0),
    ("Bailu -- White Dew (白露)",            165.0),
    ("Qiufen -- Autumnal Equinox (秋分)",    180.0),
    ("Hanlu -- Cold Dew (寒露)",             195.0),
    ("Shuangjiang -- Frost's Descent (霜降)", 210.0),
    ("Lidong -- Start of Winter (立冬)",     225.0),
    ("Xiaoxue -- Minor Snow (小雪)",         240.0),
    ("Daxue -- Major Snow (大雪)",           255.0),
    ("Dongzhi -- Winter Solstice (冬至)",    270.0),
]


# ---------------------------------------------------------------------------
# Approximate sun ecliptic longitude for a given day of year
# ---------------------------------------------------------------------------

def _sun_longitude(day_of_year: int) -> float:
    """
    Approximate ecliptic longitude of the sun in degrees.
    0° = vernal equinox (~Mar 20). Returns 0-360.
    """
    # Approximate: sun moves ~360°/365.25 days, with perihelion Jan 3
    # More accurate formula accounting for equation of center:
    mean_anomaly = math.radians((360.0 / 365.25) * (day_of_year - 2))
    # Equation of center (first-order)
    eq_center = 2 * 1.9148 * math.sin(mean_anomaly)
    # Ecliptic longitude
    lon = (mean_anomaly * 180 / math.pi + eq_center + 180 + 102.9372) % 360
    return lon


def _find_term_date(year: int, target_lon: float) -> datetime:
    """
    Binary search for the day in `year` when sun reaches `target_lon`.
    Returns the approximate date (day resolution).
    """
    # Chunfen (0°) is the only term that needs special handling
    # because longitude wraps around 360°
    # Strategy: search within a 20-day window around the expected date

    # Expected DOY: rough estimate from longitude
    # Chunfen is ~day 80, each 15° is ~15.22 days
    if target_lon == 0.0:
        # Spring equinox: ~day 79-82
        search_center = 80
    else:
        # Map longitude to approximate DOY
        # Perihelion offset: sun at 0° ecliptic lon ~Mar 20 = day 79
        # Each degree ~1.014 days
        # lon 315° = Xiaohan ~day 6, lon 270° = Dongzhi ~day 355
        if target_lon > 270:
            search_center = int((target_lon - 360) / 360 * 365.25) + 79
        else:
            search_center = int(target_lon / 360 * 365.25) + 79
        search_center = search_center % 365 or 365

    # Binary search within ±20 days of expected
    low  = max(1, search_center - 20)
    high = min(365, search_center + 20)

    def lon_at(doy: int) -> float:
        return _sun_longitude(doy)

    def angular_diff(a: float, b: float) -> float:
        """Signed angular difference a - b, in -180 to 180 range."""
        d = (a - b) % 360
        if d > 180:
            d -= 360
        return d

    # Walk day by day in the window to find the crossing
    best_doy  = search_center
    best_diff = abs(angular_diff(lon_at(search_center), target_lon))

    for doy in range(low, high + 1):
        diff = abs(angular_diff(lon_at(doy), target_lon))
        if diff < best_diff:
            best_diff = diff
            best_doy  = doy

    return datetime(year, 1, 1) + timedelta(days=best_doy - 1)


def compute(dt: datetime) -> SolarTermContext:
    doy = dt.timetuple().tm_yday
    current_lon = _sun_longitude(doy)

    # Find which term we're currently in and what's next
    # Terms are ordered by longitude starting from 285° (Xiaohan ~Jan 6)
    # We need to find the most recently passed term

    # Build all term dates for this year and next for wrap-around
    term_dates: list[tuple[datetime, str]] = []
    for year in (dt.year - 1, dt.year, dt.year + 1):
        for name, lon in _TERMS:
            term_dates.append((_find_term_date(year, lon), name))
    term_dates.sort(key=lambda x: x[0])

    # Current term = last one that started before now
    today = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    past   = [(d, n) for d, n in term_dates if d <= today]
    future = [(d, n) for d, n in term_dates if d >  today]

    current_dt, current_name = max(past, key=lambda x: x[0])
    next_dt,    next_name    = min(future, key=lambda x: x[0])

    return SolarTermContext(
        current_term       = current_name,
        current_term_start = current_dt,
        next_term          = next_name,
        next_term_date     = next_dt,
        days_to_next       = (next_dt - today).days,
    )
