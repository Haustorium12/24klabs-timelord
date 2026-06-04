"""
clock.engine.biorhythm
======================
Biorhythm cycles from birth date.

Three sinusoidal cycles, each starting at 0 on the day of birth:
  Physical:      23-day cycle  (body, strength, coordination)
  Emotional:     28-day cycle  (mood, creativity, sensitivity)
  Intellectual:  33-day cycle  (cognition, memory, analytical ability)

Values range from -100 (trough) to +100 (peak). 0 = critical day
(crossing the axis -- transitions are the most volatile days).

Requires CLOCK_BIRTH_DATE in environment (YYYY-MM-DD format).
Returns None for all fields if not configured.

No external deps. Pure stdlib math.
"""

import math
import os
from datetime import datetime, date
from ..engine.context import BiorhythmContext


def _cycle(days_alive: int, period: int) -> float:
    """Value of a sinusoidal biorhythm cycle. Returns -100 to +100."""
    return round(100 * math.sin(2 * math.pi * days_alive / period), 1)


def _load_birth_date() -> date | None:
    """Load birth date from CLOCK_BIRTH_DATE env var. Returns None if not set."""
    raw = os.environ.get("CLOCK_BIRTH_DATE", "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def compute(dt: datetime) -> BiorhythmContext:
    birth = _load_birth_date()

    if birth is None:
        return BiorhythmContext(
            physical_pct    = None,
            emotional_pct   = None,
            intellectual_pct = None,
        )

    today      = dt.date() if hasattr(dt, "date") else dt
    days_alive = (today - birth).days

    if days_alive < 0:
        # Birth date is in the future -- config error
        return BiorhythmContext(
            physical_pct    = None,
            emotional_pct   = None,
            intellectual_pct = None,
        )

    return BiorhythmContext(
        physical_pct     = _cycle(days_alive, 23),
        emotional_pct    = _cycle(days_alive, 28),
        intellectual_pct = _cycle(days_alive, 33),
    )
