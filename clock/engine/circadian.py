"""
clock.engine.circadian
======================
Biological time -- maps the current hour to human energy/hormonal phases
and computes the photoperiod trend (daylight gaining or losing vs yesterday).

Phase lookup order:
  1. schedule param  (injected by API from caller's profile)
  2. Generic fallback (morning-chronotype population averages)

Profiles are loaded by the API layer (server.py) and passed in via
assemble(schedule=...) -> compute(dt, lat, schedule=...).
This module has no filesystem access -- clean separation.

No external deps. Pure stdlib.
"""

from datetime import datetime, timedelta
import math
from typing import Optional
from ..engine.context import CircadianContext


# ---------------------------------------------------------------------------
# Schedule window matching
# ---------------------------------------------------------------------------

def _hhmm_to_minutes(hhmm: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_window(now_min: int, start_min: int, end_min: int) -> bool:
    """
    Check if now_min falls in [start_min, end_min).
    Handles midnight wrap (e.g. 23:30 to 01:45).
    """
    if start_min < end_min:
        return start_min <= now_min < end_min
    else:
        return now_min >= start_min or now_min < end_min


def _phase_from_schedule(
    hour: int, minute: int, schedule: list
) -> Optional[tuple[str, str, str]]:
    """
    Look up current time in a schedule list.
    Returns (label, energy_phase, suitable_for) or None if no match.
    """
    now_min = hour * 60 + minute
    for entry in schedule:
        try:
            start = _hhmm_to_minutes(entry["start"])
            end   = _hhmm_to_minutes(entry["end"])
            if _in_window(now_min, start, end):
                return entry["label"], entry["energy_phase"], entry["suitable_for"]
        except (KeyError, ValueError):
            continue
    return None


# ---------------------------------------------------------------------------
# Generic fallback -- morning-chronotype population averages
# ---------------------------------------------------------------------------

def _energy_phase(hour: int) -> tuple[str, str, str]:
    """
    Returns (label, energy_phase, suitable_for) for a given 24h hour.
    Generic morning-chronotype fallback used when no profile schedule is available.
    """
    if 5 <= hour < 9:
        return (
            "Early Morning",
            "Cortisol rising -- alertness building",
            "Light tasks, planning, morning routine, exercise",
        )
    elif 9 <= hour < 12:
        return (
            "Late Morning",
            "Cortisol peak -- peak cognitive performance",
            "Deep work, complex analysis, difficult decisions, learning",
        )
    elif 12 <= hour < 14:
        return (
            "Midday",
            "Post-peak -- slight dip approaching",
            "Meetings, collaborative work, administrative tasks",
        )
    elif 14 <= hour < 17:
        return (
            "Afternoon",
            "Secondary alertness -- physical peak",
            "Creative work, physical tasks, brainstorming",
        )
    elif 17 <= hour < 21:
        return (
            "Evening",
            "Cortisol falling -- melatonin beginning",
            "Reflection, light reading, social connection, winding down",
        )
    elif 21 <= hour < 24:
        return (
            "Night",
            "Melatonin rising -- preparation for sleep",
            "Journaling, gentle creative work, avoid screens and hard decisions",
        )
    else:  # 0-4
        return (
            "Deep Night",
            "Melatonin peak -- should be asleep",
            "Nothing if possible -- body repair and memory consolidation is happening",
        )


# ---------------------------------------------------------------------------
# Photoperiod trend
# ---------------------------------------------------------------------------

def _solar_daylight_minutes(day_of_year: int, lat: float) -> float:
    """
    Approximate daylight minutes for a given day of year and latitude.
    Uses the same NOAA-derived formula as solar.py but simplified for
    yesterday/today comparison (we only need the difference, not exact times).
    """
    gamma = 2 * math.pi / 365 * (day_of_year - 1)
    decl  = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148  * math.sin(3 * gamma)
    )
    cos_ha = (
        math.cos(math.radians(90.833))
        / (math.cos(math.radians(lat)) * math.cos(decl))
        - math.tan(math.radians(lat)) * math.tan(decl)
    )
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha = math.degrees(math.acos(cos_ha))
    return ha * 8


def _photoperiod_trend(dt: datetime, lat: float) -> tuple[str, float]:
    """
    Returns (trend_label, minutes_vs_yesterday).
    Positive = gaining daylight. Negative = losing.
    """
    today     = dt.timetuple().tm_yday
    yesterday = (dt - timedelta(days=1)).timetuple().tm_yday

    today_min     = _solar_daylight_minutes(today, lat)
    yesterday_min = _solar_daylight_minutes(yesterday, lat)
    delta         = today_min - yesterday_min

    if abs(delta) < 0.1:
        trend = "Stable (near solstice)"
    elif delta > 0:
        trend = "Lengthening"
    else:
        trend = "Shortening"

    return trend, round(delta, 1)


# ---------------------------------------------------------------------------
# Public compute
# ---------------------------------------------------------------------------

def compute(
    dt: datetime,
    lat: float,
    schedule: Optional[list] = None,
) -> CircadianContext:
    """
    Compute circadian context for the given moment.

    Args:
        dt:       The datetime to evaluate.
        lat:      Latitude for photoperiod calculation.
        schedule: Optional personal schedule (list of window dicts with
                  start/end/label/energy_phase/suitable_for). When provided,
                  overrides the generic morning-chronotype map.
                  Injected by the API from the caller's profile.
    """
    if schedule:
        phase = _phase_from_schedule(dt.hour, dt.minute, schedule)
        if phase:
            label, energy_phase, suitable = phase
        else:
            label, energy_phase, suitable = _energy_phase(dt.hour)
    else:
        label, energy_phase, suitable = _energy_phase(dt.hour)

    trend, delta = _photoperiod_trend(dt, lat)

    return CircadianContext(
        label                = label,
        energy_phase         = energy_phase,
        suitable_for         = suitable,
        photoperiod_trend    = trend,
        minutes_vs_yesterday = delta,
    )
