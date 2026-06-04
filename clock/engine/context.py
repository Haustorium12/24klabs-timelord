"""
clock.engine.context
====================
TemporalContext: the single data structure that the full engine produces.
Every engine module fills its section. The assembler (engine/__init__.py)
calls them all and returns one TemporalContext.

Frozen dataclass -- computed once, never mutated.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SolarContext:
    sunrise_local: str          # "5:54 AM"
    solar_noon_local: str       # "12:56 PM"
    sunset_local: str           # "7:58 PM"
    daylight_hours: float       # 14.07
    daylight_hm: str            # "14h 04m"
    golden_hour_start: str      # "7:02 PM"
    golden_hour_end: str        # "7:58 PM"


@dataclass(frozen=True)
class LunarContext:
    phase_name: str             # "Waxing Crescent"
    age_days: float             # 5.1
    cycle_pct: float            # 17.3
    prev_new: datetime
    next_new: datetime
    prev_full: datetime
    next_full: datetime
    full_moon_name_this_month: str   # "Flower Moon"
    full_moon_name_next: str


@dataclass(frozen=True)
class WheelContext:
    last_sabbat_name: str
    last_sabbat_date: datetime
    last_sabbat_type: str
    last_sabbat_days_ago: int
    next_sabbat_name: str
    next_sabbat_date: datetime
    next_sabbat_type: str
    next_sabbat_days_away: int
    ladder: list[tuple[str, datetime, str]]  # (name, date, type)


@dataclass(frozen=True)
class AstrologyContext:
    sun_sign: str               # "Taurus"
    element: str                # "Earth"
    modality: str               # "Fixed"
    ruler: str                  # "Venus"
    day_name: str               # "Sunday"
    day_planet: str             # "Sun"
    day_color: str
    day_metal: str
    day_stones: str
    day_use: str
    next_ingress_sign: str
    next_ingress_date: datetime


@dataclass(frozen=True)
class CalendarContext:
    """Gregorian calendar position."""
    iso_week: int
    day_of_year: int
    days_in_year: int
    day_of_month: int
    days_in_month: int
    quarter: int
    week_pct: float
    year_pct: float
    month_pct: float


@dataclass(frozen=True)
class SiderealContext:
    julian_date: float
    holocene_year: int          # HE 12026
    sidereal_time_hours: float  # Greenwich Mean Sidereal Time


@dataclass(frozen=True)
class AlternativeCalendars:
    """convertdate-powered calendar systems. All optional -- None if unavailable."""
    hebrew: Optional[str]       # e.g. "5 Sivan 5786"
    islamic: Optional[str]      # e.g. "19 Dhul-Qadah 1447"
    chinese: Optional[str]      # e.g. "Year of the Snake, Month 4, Day 20"
    persian: Optional[str]      # e.g. "27 Ordibehesht 1405"
    mayan_long_count: Optional[str]   # e.g. "13.0.13.10.6"
    ethiopian: Optional[str]
    coptic: Optional[str]
    julian: Optional[str]       # Julian calendar (not Julian Date)


@dataclass(frozen=True)
class VedicContext:
    tithi: str                  # lunar day + fortnight
    nakshatra: str              # lunar mansion (approximate)
    paksha: str                 # "Shukla" (waxing) or "Krishna" (waning)


@dataclass(frozen=True)
class CircadianContext:
    label: str                  # "Morning", "Afternoon", etc.
    energy_phase: str           # "Cortisol rising -- high focus"
    suitable_for: str           # "Deep work, planning, learning"
    photoperiod_trend: str      # "Lengthening" / "Shortening"
    minutes_vs_yesterday: float # daylight minutes gained/lost


@dataclass(frozen=True)
class MarketContext:
    is_trading_day: bool
    session_status: str         # "Pre-market", "Open", "After-hours", "Closed"
    days_to_quarter_end: int
    quarter_end_date: datetime


@dataclass(frozen=True)
class BiorhythmContext:
    """Requires birth date. None if not configured."""
    physical_pct: Optional[float]    # 23-day cycle, -100 to +100
    emotional_pct: Optional[float]   # 28-day cycle
    intellectual_pct: Optional[float] # 33-day cycle


@dataclass(frozen=True)
class SolarTermContext:
    """Chinese 24 Jieqi solar terms."""
    current_term: str           # e.g. "Grain Buds (小满)"
    current_term_start: datetime
    next_term: str
    next_term_date: datetime
    days_to_next: int


@dataclass(frozen=True)
class PlanetContext:
    """Skyfield addon -- None if addon not enabled."""
    sun_ra: Optional[float]
    sun_dec: Optional[float]
    moon_ra: Optional[float]
    moon_dec: Optional[float]
    mercury: Optional[str]
    venus: Optional[str]
    mars: Optional[str]
    jupiter: Optional[str]
    saturn: Optional[str]


# ---------------------------------------------------------------------------
# Root context -- the full assembled output
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemporalContext:
    """
    The complete temporal snapshot for a given moment.
    Produced by clock.engine.assemble(dt).
    """
    generated_at: datetime
    timezone_name: str          # "America/New_York"

    gregorian: CalendarContext
    solar: SolarContext
    lunar: LunarContext
    wheel: WheelContext
    astrology: AstrologyContext
    sidereal: SiderealContext
    alternative: AlternativeCalendars
    vedic: VedicContext
    circadian: CircadianContext
    market: MarketContext
    biorhythm: BiorhythmContext
    solar_terms: SolarTermContext
    planets: Optional[PlanetContext] = None
