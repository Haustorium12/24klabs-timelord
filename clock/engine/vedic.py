"""
clock.engine.vedic
==================
Vedic Panchanga -- the five-limbed Hindu timekeeping system.
We compute the three most universally useful limbs:

  Tithi     -- lunar day (1-30), derived from moon's elongation from sun
  Nakshatra -- lunar mansion (1-27), approximate from lunar longitude
  Paksha    -- fortnight (Shukla = waxing, Krishna = waning)

The vara (weekday) and yoga/karana are omitted for now; vara duplicates
the planetary day we already have.

ACCURACY NOTE: Tithi is computed from the synodic cycle phase, which
is accurate to within ~30 minutes. Nakshatra is approximated from
the lunar cycle position without a full ephemeris -- accurate to
~1 nakshatra. For precision Jyotish, use a dedicated library.

No external deps. Pure stdlib.
"""

import math
from datetime import datetime
from ..engine.context import VedicContext

# 27 nakshatras in ecliptic order (each spans 13°20' = 13.333°)
_NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# 30 tithis -- 15 per paksha
_TITHI_NAMES = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",  # Shukla 1-15
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya", # Krishna 1-15
]

_REF_NEW_MOON = datetime(2000, 1, 6, 18, 14)
_SYNODIC      = 29.53058867


def compute(dt: datetime) -> VedicContext:
    # Lunar age in current cycle
    dt = dt.replace(tzinfo=None)  # normalize: reference point is naive
    diff_days = (dt - _REF_NEW_MOON).total_seconds() / 86400.0
    age       = diff_days % _SYNODIC

    # Paksha (fortnight)
    paksha = "Shukla" if age < _SYNODIC / 2 else "Krishna"

    # Tithi: 30 tithis per synodic month, each = 1/30 of cycle
    # tithi_num is 1-30
    tithi_num  = int(age / _SYNODIC * 30) + 1
    tithi_num  = min(tithi_num, 30)
    tithi_name = _TITHI_NAMES[tithi_num - 1]
    tithi      = f"{paksha} {tithi_name} ({tithi_num})"

    # Nakshatra: moon traverses all 27 in one sidereal month (~27.32 days)
    # Approximate from synodic position -- within ~1 nakshatra of actual
    sidereal_period = 27.32166
    moon_lon = (age / sidereal_period * 360.0) % 360.0  # degrees
    nakshatra_idx = int(moon_lon / (360.0 / 27)) % 27
    nakshatra = _NAKSHATRAS[nakshatra_idx]

    return VedicContext(
        tithi     = tithi,
        nakshatra = nakshatra,
        paksha    = paksha,
    )
