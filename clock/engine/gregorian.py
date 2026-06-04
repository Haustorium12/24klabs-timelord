"""
clock.engine.gregorian
======================
Gregorian calendar position for a given datetime.
No external deps. Pure stdlib.
"""

import calendar
from datetime import datetime
from ..engine.context import CalendarContext


def compute(dt: datetime) -> CalendarContext:
    iso_week      = dt.isocalendar()[1]
    day_of_year   = dt.timetuple().tm_yday
    days_in_year  = 366 if calendar.isleap(dt.year) else 365
    day_of_month  = dt.day
    days_in_month = calendar.monthrange(dt.year, dt.month)[1]
    quarter       = (dt.month - 1) // 3 + 1
    dow           = dt.weekday()  # 0=Monday

    return CalendarContext(
        iso_week      = iso_week,
        day_of_year   = day_of_year,
        days_in_year  = days_in_year,
        day_of_month  = day_of_month,
        days_in_month = days_in_month,
        quarter       = quarter,
        week_pct      = round((dow + 1) / 7 * 100, 1),
        year_pct      = round(day_of_year / days_in_year * 100, 1),
        month_pct     = round(day_of_month / days_in_month * 100, 1),
    )
