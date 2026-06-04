"""
clock.engine.solar
==================
Sunrise, sunset, solar noon, golden hour.
Algorithm: NOAA equation of time + solar declination.
Accurate to ~1 minute for mid-latitudes.

No external deps. Pure stdlib math.
"""

import math
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo
from ..engine.context import SolarContext


def _solar_minutes(dt: datetime, lat: float, lon: float) -> tuple[float, float]:
    """
    Returns (sunrise_utc_min, sunset_utc_min) as minutes since midnight UTC.
    Pure NOAA equation-of-time implementation.
    """
    n     = dt.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (n - 1)

    # Equation of time (minutes) -- accounts for Earth's elliptical orbit
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    # Solar declination (radians) -- angle of sun relative to equator
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148  * math.sin(3 * gamma)
    )

    # Hour angle at sunrise (90.833° accounts for refraction + solar disk radius)
    cos_ha = (
        math.cos(math.radians(90.833))
        / (math.cos(math.radians(lat)) * math.cos(decl))
        - math.tan(math.radians(lat)) * math.tan(decl)
    )
    cos_ha = max(-1.0, min(1.0, cos_ha))  # clamp for polar edge cases
    ha = math.degrees(math.acos(cos_ha))

    # UTC minutes since midnight
    sunrise_utc = 720 - 4 * (lon + ha) - eqtime
    sunset_utc  = 720 - 4 * (lon - ha) - eqtime

    return sunrise_utc, sunset_utc


def _minutes_to_time(utc_minutes: float, tz: ZoneInfo) -> time:
    """Convert UTC minutes-since-midnight to a local time object."""
    # Build a UTC datetime for today at utc_minutes
    base = datetime.now(tz=timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    dt_utc = base + timedelta(minutes=utc_minutes)
    dt_local = dt_utc.astimezone(tz)
    return dt_local.time()


def _fmt(t: time) -> str:
    """Format a time object as '5:54 AM' (no leading zero on hour)."""
    h  = t.hour
    m  = t.minute
    suffix = "AM" if h < 12 else "PM"
    h12    = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def compute(dt: datetime, lat: float, lon: float, tz: ZoneInfo) -> SolarContext:
    sunrise_utc, sunset_utc = _solar_minutes(dt, lat, lon)

    sunrise_t     = _minutes_to_time(sunrise_utc, tz)
    sunset_t      = _minutes_to_time(sunset_utc, tz)
    solar_noon_t  = _minutes_to_time((sunrise_utc + sunset_utc) / 2, tz)
    golden_start_t = _minutes_to_time(sunset_utc - 56, tz)  # ~56 min golden window

    daylight_min  = sunset_utc - sunrise_utc
    daylight_h    = daylight_min / 60.0
    dh, dm        = int(daylight_h), int((daylight_h % 1) * 60)

    return SolarContext(
        sunrise_local    = _fmt(sunrise_t),
        solar_noon_local = _fmt(solar_noon_t),
        sunset_local     = _fmt(sunset_t),
        daylight_hours   = round(daylight_h, 3),
        daylight_hm      = f"{dh}h {dm:02d}m",
        golden_hour_start = _fmt(golden_start_t),
        golden_hour_end  = _fmt(sunset_t),
    )
