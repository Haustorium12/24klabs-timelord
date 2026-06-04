"""
clock.engine.astrology
======================
Sun sign (tropical zodiac) + next ingress date.
Planetary day correspondences (planet, color, metal, stones, use).

No external deps. Pure stdlib.
"""

from datetime import datetime
from ..engine.context import AstrologyContext


# ---------------------------------------------------------------------------
# Zodiac
# Each entry: (sign, (start_month, start_day), element, modality, ruler)
# Sorted in calendar order. Capricorn wraps Dec->Jan, handled separately.
# ---------------------------------------------------------------------------

_ZODIAC = [
    ("Aquarius",    ( 1, 20), "Air",   "Fixed",    "Uranus/Saturn"),
    ("Pisces",      ( 2, 19), "Water", "Mutable",  "Neptune/Jupiter"),
    ("Aries",       ( 3, 21), "Fire",  "Cardinal", "Mars"),
    ("Taurus",      ( 4, 20), "Earth", "Fixed",    "Venus"),
    ("Gemini",      ( 5, 21), "Air",   "Mutable",  "Mercury"),
    ("Cancer",      ( 6, 21), "Water", "Cardinal", "Moon"),
    ("Leo",         ( 7, 23), "Fire",  "Fixed",    "Sun"),
    ("Virgo",       ( 8, 23), "Earth", "Mutable",  "Mercury"),
    ("Libra",       ( 9, 23), "Air",   "Cardinal", "Venus"),
    ("Scorpio",     (10, 23), "Water", "Fixed",    "Pluto/Mars"),
    ("Sagittarius", (11, 22), "Fire",  "Mutable",  "Jupiter"),
    ("Capricorn",   (12, 22), "Earth", "Cardinal", "Saturn"),
    # Aquarius repeated at year boundary -- Capricorn runs to Jan 19
]


def _zodiac_for(dt: datetime) -> tuple[str, str, str, str]:
    """Return (sign, element, modality, ruler) for a given date."""
    m, d = dt.month, dt.day

    # Capricorn straddles Dec 22 -- Jan 19
    if (m == 12 and d >= 22) or (m == 1 and d <= 19):
        return ("Capricorn", "Earth", "Cardinal", "Saturn")

    # All other signs: find the last entry whose start date has passed
    current = ("Aquarius", "Air", "Fixed", "Uranus/Saturn")  # default
    for sign, (sm, sd), elem, modal, ruler in _ZODIAC:
        if (m > sm) or (m == sm and d >= sd):
            current = (sign, elem, modal, ruler)
    return current


def _next_ingress(dt: datetime) -> tuple[str, datetime]:
    """Return (next_sign, ingress_date) for the next sun sign change."""
    # Build ingress dates for this year and next
    ingresses: list[tuple[datetime, str]] = []
    for year in (dt.year, dt.year + 1):
        # Capricorn boundary
        ingresses.append((datetime(year,  1, 20), "Aquarius"))
        for sign, (sm, sd), *_ in _ZODIAC:
            ingresses.append((datetime(year, sm, sd), sign))

    # Filter to future only, take nearest
    dt_naive = dt.replace(tzinfo=None)
    future = [(d, s) for d, s in ingresses if d > dt_naive]
    future.sort(key=lambda x: x[0])
    next_date, next_sign = future[0]
    return next_sign, next_date


# ---------------------------------------------------------------------------
# Planetary day table
# key = weekday() (0=Monday ... 6=Sunday)
# ---------------------------------------------------------------------------

_PLANETARY_DAY: dict[int, tuple[str, str, str, str, str, str]] = {
    0: ("Monday",    "Moon",    "silver",      "silver, moonstone, pearl",        "white, silver",  "intuition, dreams, womb-work, water magic"),
    1: ("Tuesday",   "Mars",    "iron",        "bloodstone, ruby, garnet",         "red",            "courage, severance, protection, will-work"),
    2: ("Wednesday", "Mercury", "quicksilver", "agate, opal",                      "yellow, orange", "communication, travel, study, divination"),
    3: ("Thursday",  "Jupiter", "tin",         "amethyst, sapphire",               "purple, blue",   "expansion, prosperity, justice, oaths"),
    4: ("Friday",    "Venus",   "copper",      "rose quartz, emerald",             "green, pink",    "love, beauty, art, friendship"),
    5: ("Saturday",  "Saturn",  "lead",        "onyx, jet, obsidian",              "black",          "binding, banishing, time-work, ancestors"),
    6: ("Sunday",    "Sun",     "gold",        "citrine, amber, topaz",            "yellow, gold",   "vitality, sovereignty, healing, success"),
}


def compute(dt: datetime) -> AstrologyContext:
    sign, elem, modal, ruler = _zodiac_for(dt)
    next_sign, next_date     = _next_ingress(dt)

    day_name, planet, metal, stones, color, use = _PLANETARY_DAY[dt.weekday()]

    return AstrologyContext(
        sun_sign          = sign,
        element           = elem,
        modality          = modal,
        ruler             = ruler,
        day_name          = day_name,
        day_planet        = planet,
        day_color         = color,
        day_metal         = metal,
        day_stones        = stones,
        day_use           = use,
        next_ingress_sign = next_sign,
        next_ingress_date = next_date,
    )
