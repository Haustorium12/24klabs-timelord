"""
clock.engine.assemble
=====================
The single public entry point for the engine layer.

    from clock.engine.assemble import assemble
    ctx = assemble()           # uses now + config defaults
    ctx = assemble(dt=some_dt) # specific moment

Calls all engine modules, assembles TemporalContext.
Optional modules (planets, biorhythm, convertdate calendars) fail
gracefully -- a bad optional module never kills the whole context.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .. import config
from .context import TemporalContext
from . import gregorian, solar, lunar, wheel, astrology, sidereal
from . import calendars, vedic, circadian, market, solar_terms, biorhythm

log = logging.getLogger(__name__)


def assemble(
    dt: datetime | None = None,
    schedule: list | None = None,
) -> TemporalContext:
    """
    Compute a full TemporalContext for the given moment.
    If dt is None, uses datetime.now() in the configured timezone.
    Runtime: ~2-5ms typical.
    """
    tz: ZoneInfo = config.TIMEZONE

    if dt is None:
        dt = datetime.now(tz=tz)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)

    lat = config.LAT
    lon = config.LON

    # ------------------------------------------------------------------ #
    # Core modules -- always run, stdlib only                             #
    # ------------------------------------------------------------------ #

    greg         = gregorian.compute(dt)
    sol          = solar.compute(dt, lat, lon, tz)
    lun          = lunar.compute(dt)
    whl          = wheel.compute(dt)
    astro        = astrology.compute(dt)
    sid          = sidereal.compute(dt)
    circ         = circadian.compute(dt, lat, schedule=schedule)
    mkt          = market.compute(dt)
    vdic         = vedic.compute(dt)
    bio          = biorhythm.compute(dt)

    # ------------------------------------------------------------------ #
    # Solar terms -- stdlib only but complex; guard just in case          #
    # ------------------------------------------------------------------ #
    try:
        sol_terms = solar_terms.compute(dt)
    except Exception as exc:
        log.warning("solar_terms failed: %s", exc)
        from .context import SolarTermContext
        sol_terms = SolarTermContext(
            current_term="Unknown", current_term_start=dt,
            next_term="Unknown", next_term_date=dt, days_to_next=0,
        )

    # ------------------------------------------------------------------ #
    # Optional: convertdate calendar systems                              #
    # ------------------------------------------------------------------ #
    try:
        alt = calendars.compute(dt)
    except Exception as exc:
        log.warning("calendars failed: %s", exc)
        from .context import AlternativeCalendars
        alt = AlternativeCalendars(
            hebrew=None, islamic=None, chinese=None,
            persian=None, mayan_long_count=None,
            ethiopian=None, coptic=None, julian=None,
        )

    # ------------------------------------------------------------------ #
    # Optional: skyfield planet positions                                  #
    # ------------------------------------------------------------------ #
    planets = None
    if config.PLANETS_ENABLED:
        try:
            from ..addons import planets as planet_mod
            planets = planet_mod.compute(dt)
        except Exception as exc:
            log.warning("planets addon failed: %s", exc)

    return TemporalContext(
        generated_at  = dt,
        timezone_name = str(tz),
        gregorian     = greg,
        solar         = sol,
        lunar         = lun,
        wheel         = whl,
        astrology     = astro,
        sidereal      = sid,
        alternative   = alt,
        vedic         = vdic,
        circadian     = circ,
        market        = mkt,
        biorhythm     = bio,
        solar_terms   = sol_terms,
        planets       = planets,
    )
