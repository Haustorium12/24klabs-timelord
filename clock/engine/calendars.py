"""
clock.engine.calendars
======================
Alternative calendar systems.

Dependencies (all optional -- null fields if absent):
  convertdate  -- Hebrew, Islamic, Persian, Coptic, Julian, Mayan
  lunardate    -- Chinese lunisolar (not in convertdate 2.4.x)

Install: pip install convertdate lunardate

Ethiopian calendar is derived from Coptic (same epoch, year + 276,
different month names) -- no extra library needed.
"""

from datetime import datetime
from ..engine.context import AlternativeCalendars

# ---------------------------------------------------------------------------
# Month name tables
# ---------------------------------------------------------------------------

_HEBREW_MONTHS = [
    "", "Nisan", "Iyyar", "Sivan", "Tammuz", "Av", "Elul",
    "Tishri", "Cheshvan", "Kislev", "Tevet", "Shevat",
    "Adar", "Adar II",
]

_ISLAMIC_MONTHS = [
    "", "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
    "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhul-Qadah", "Dhul-Hijjah",
]

_ETHIOPIAN_MONTHS = [
    "", "Meskerem", "Tikemt", "Hidar", "Tahsas", "Tir", "Yekatit",
    "Megabit", "Miazia", "Ginbot", "Sene", "Hamle", "Nehase", "Pagume",
]

_COPTIC_MONTHS = [
    "", "Thout", "Paopi", "Hathor", "Koiak", "Tobi", "Meshir",
    "Paremhat", "Parmouti", "Pashons", "Paoni", "Epip", "Mesori", "Pi Kogi Enavot",
]

_PERSIAN_MONTHS = [
    "", "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
    "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand",
]

# Zodiac cycle starting from 2020 (Year of the Rat = index 0)
_CHINESE_ZODIAC = [
    "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
    "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
]

# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

def compute(dt: datetime) -> AlternativeCalendars:
    g = (dt.year, dt.month, dt.day)

    # ------------------------------------------------------------------ #
    # convertdate -- Hebrew, Islamic, Persian, Coptic, Mayan, Julian      #
    # ------------------------------------------------------------------ #
    hebrew = islamic = persian = coptic = mayan_long_count = julian = None
    coptic_year = coptic_month = coptic_day = None

    try:
        from convertdate import hebrew as _heb
        hy, hm, hd = _heb.from_gregorian(*g)
        name = _HEBREW_MONTHS[hm] if hm < len(_HEBREW_MONTHS) else str(hm)
        hebrew = f"{hd} {name} {hy}"
    except Exception:
        pass

    try:
        from convertdate import islamic as _isl
        iy, im, id_ = _isl.from_gregorian(*g)
        name = _ISLAMIC_MONTHS[im] if im < len(_ISLAMIC_MONTHS) else str(im)
        islamic = f"{id_} {name} {iy}"
    except Exception:
        pass

    try:
        from convertdate import persian as _per
        py, pm, pd = _per.from_gregorian(*g)
        name = _PERSIAN_MONTHS[pm] if pm < len(_PERSIAN_MONTHS) else str(pm)
        persian = f"{pd} {name} {py}"
    except Exception:
        pass

    try:
        from convertdate import coptic as _cop
        coy, com, cod = _cop.from_gregorian(*g)
        coptic_year, coptic_month, coptic_day = coy, com, cod
        name = _COPTIC_MONTHS[com] if com < len(_COPTIC_MONTHS) else str(com)
        coptic = f"{cod} {name} {coy}"
    except Exception:
        pass

    try:
        from convertdate import mayan as _may
        baktun, katun, tun, uinal, kin = _may.from_gregorian(*g)
        mayan_long_count = f"{baktun}.{katun}.{tun}.{uinal}.{kin}"
    except Exception:
        pass

    try:
        from convertdate import julian as _jul
        jy, jm, jd_ = _jul.from_gregorian(*g)
        julian = f"{dt.strftime('%A')}, {jm:02d}/{jd_:02d}/{jy} (Julian calendar)"
    except Exception:
        pass

    # ------------------------------------------------------------------ #
    # Ethiopian -- derived from Coptic (same epoch, year offset +276)     #
    # No extra library needed.                                             #
    # ------------------------------------------------------------------ #
    ethiopian = None
    if coptic_year is not None:
        try:
            ey = coptic_year + 276
            name = _ETHIOPIAN_MONTHS[coptic_month] if coptic_month < len(_ETHIOPIAN_MONTHS) else str(coptic_month)
            ethiopian = f"{coptic_day} {name} {ey}"
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Chinese -- lunardate library                                        #
    # ------------------------------------------------------------------ #
    chinese = None
    try:
        from lunardate import LunarDate
        ld = LunarDate.fromSolarDate(*g)
        zodiac = _CHINESE_ZODIAC[(ld.year - 2020) % 12]
        leap_tag = " (leap)" if ld.isLeapMonth else ""
        chinese = f"Year of the {zodiac}, Month {ld.month}{leap_tag}, Day {ld.day}"
    except Exception:
        pass

    return AlternativeCalendars(
        hebrew=hebrew,
        islamic=islamic,
        chinese=chinese,
        persian=persian,
        mayan_long_count=mayan_long_count,
        ethiopian=ethiopian,
        coptic=coptic,
        julian=julian,
    )
