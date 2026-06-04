"""
clock.engine.market
===================
US equity market calendar context.

  - Is today a trading day?
  - What is the current session status?
  - How many days to quarter end?

US market hours: 9:30 AM - 4:00 PM Eastern.
Pre-market: 4:00 AM - 9:30 AM. After-hours: 4:00 PM - 8:00 PM.

Holidays are computed for the current year. The rule-based approach
handles most US market holidays correctly for near-term years.
Early closes (day before Thanksgiving, July 4 eve) are noted but
not modeled as 1pm closes since that complexity rarely matters for AI context.

No external deps. Pure stdlib.
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from ..engine.context import MarketContext

_EASTERN = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Holiday computation
# ---------------------------------------------------------------------------

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """nth occurrence of a weekday (0=Mon) in a given month."""
    d = date(year, month, 1)
    # Advance to first occurrence of weekday
    d += timedelta(days=(weekday - d.weekday()) % 7)
    # Advance to nth occurrence
    d += timedelta(weeks=n - 1)
    return d


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Last occurrence of a weekday in a given month."""
    # Start from the last day of the month, walk back
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    diff = (last.weekday() - weekday) % 7
    return last - timedelta(days=diff)


def _observed(d: date) -> date:
    """If a fixed holiday falls on a weekend, return the observed weekday."""
    if d.weekday() == 5:   # Saturday -> Friday
        return d - timedelta(days=1)
    elif d.weekday() == 6: # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def _us_market_holidays(year: int) -> set[date]:
    """Compute NYSE holiday schedule for a given year."""
    holidays = {
        _observed(date(year,  1,  1)),  # New Year's Day
        _nth_weekday(year, 1, 0, 3),    # MLK Day (3rd Monday Jan)
        _nth_weekday(year, 2, 0, 3),    # Presidents Day (3rd Monday Feb)
        # Good Friday: Easter - 2 days
        _easter(year) - timedelta(days=2),
        _last_weekday(year, 5, 0),      # Memorial Day (last Monday May)
        _observed(date(year,  6, 19)),  # Juneteenth
        _observed(date(year,  7,  4)),  # Independence Day
        _nth_weekday(year, 9, 0, 1),    # Labor Day (1st Monday Sep)
        _nth_weekday(year, 11, 3, 4),   # Thanksgiving (4th Thursday Nov)
        _observed(date(year, 12, 25)),  # Christmas
    }
    return holidays


def _easter(year: int) -> date:
    """Anonymous Gregorian Easter algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


# ---------------------------------------------------------------------------
# Session status
# ---------------------------------------------------------------------------

def _session_status(dt_eastern: datetime) -> str:
    """Determine market session from Eastern local time."""
    h, m = dt_eastern.hour, dt_eastern.minute
    minutes = h * 60 + m

    pre_open  = 4   * 60        # 4:00 AM
    open_     = 9   * 60 + 30  # 9:30 AM
    close     = 16  * 60        # 4:00 PM
    after_end = 20  * 60        # 8:00 PM

    if   minutes < pre_open:  return "Closed (overnight)"
    elif minutes < open_:     return "Pre-market"
    elif minutes < close:     return "Open"
    elif minutes < after_end: return "After-hours"
    else:                     return "Closed (overnight)"


# ---------------------------------------------------------------------------
# Quarter end
# ---------------------------------------------------------------------------

def _quarter_end(dt: date) -> date:
    """Return the date of the end of the current quarter."""
    quarter = (dt.month - 1) // 3 + 1
    end_month = quarter * 3
    # Last day of end_month
    if end_month == 12:
        return date(dt.year + 1, 1, 1) - timedelta(days=1)
    return date(dt.year, end_month + 1, 1) - timedelta(days=1)


# ---------------------------------------------------------------------------
# Public compute
# ---------------------------------------------------------------------------

def compute(dt: datetime) -> MarketContext:
    # Convert to Eastern for session logic
    dt_eastern = dt.astimezone(_EASTERN) if dt.tzinfo else dt

    today    = dt_eastern.date()
    holidays = _us_market_holidays(today.year)

    is_trading = (
        today.weekday() < 5      # Mon-Fri
        and today not in holidays
    )

    session = _session_status(dt_eastern) if is_trading else "Closed (holiday or weekend)"

    qe_date     = _quarter_end(today)
    days_to_qe  = (qe_date - today).days

    return MarketContext(
        is_trading_day      = is_trading,
        session_status      = session,
        days_to_quarter_end = days_to_qe,
        quarter_end_date    = datetime(qe_date.year, qe_date.month, qe_date.day),
    )
