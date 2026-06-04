"""
clock.engine.renderer
=====================
Converts TemporalContext into the three formats consumers need:

  to_dict(ctx)      → JSON-serializable dict (for /now endpoint)
  to_prompt(ctx)    → compact text for Time Lord Ollama prompt
  to_markdown(ctx)  → full markdown document (for file writer)

Centralizing rendering here means no other module needs to know
the internal shape of TemporalContext.
"""

from __future__ import annotations
import dataclasses
from datetime import datetime
from typing import Any

from .context import TemporalContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.strftime("%Y-%m-%d")


def _dtiso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _opt(v: Any) -> Any:
    return v  # pass-through; None is valid JSON


# ---------------------------------------------------------------------------
# to_dict -- JSON-serializable
# ---------------------------------------------------------------------------

def to_dict(ctx: TemporalContext) -> dict:
    """Recursively convert TemporalContext to a JSON-safe dict."""

    def _convert(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: _convert(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, (list, tuple)):
            return [_convert(i) for i in obj]
        return obj

    return _convert(ctx)


# ---------------------------------------------------------------------------
# to_prompt -- compact text for Time Lord Ollama context
# ---------------------------------------------------------------------------

def to_prompt(ctx: TemporalContext) -> str:
    """Compact temporal context for injection into Ollama prompt."""
    c = ctx
    g = c.gregorian
    s = c.solar
    l = c.lunar
    w = c.wheel
    a = c.astrology
    si = c.sidereal
    ci = c.circadian
    m = c.market
    v = c.vedic
    st = c.solar_terms

    lines = [
        f"TEMPORAL CONTEXT -- {c.generated_at.strftime('%Y-%m-%d %H:%M')} {c.timezone_name}",
        "",
        f"GREGORIAN: {c.generated_at.strftime('%A, %B %d, %Y')} | "
        f"Week {g.iso_week} of 52 | Q{g.quarter} | "
        f"{g.year_pct}% through the year",

        f"SOLAR: Sunrise {s.sunrise_local} | Noon {s.solar_noon_local} | "
        f"Sunset {s.sunset_local} | Daylight {s.daylight_hm} | "
        f"Golden hour {s.golden_hour_start}-{s.golden_hour_end} | "
        f"Photoperiod {ci.photoperiod_trend} ({ci.minutes_vs_yesterday:+.1f}m vs yesterday)",

        f"LUNAR: {l.phase_name}, age {l.age_days}d ({l.cycle_pct:.1f}% cycle) | "
        f"Next new {_dt(l.next_new)} | "
        f"Next full {_dt(l.next_full)} -- {l.full_moon_name_next}",

        f"WHEEL: Last {w.last_sabbat_name} {_dt(w.last_sabbat_date)} "
        f"({w.last_sabbat_days_ago}d ago) | "
        f"Next {w.next_sabbat_name} {_dt(w.next_sabbat_date)} "
        f"(in {w.next_sabbat_days_away}d, {w.next_sabbat_type})",

        f"ASTROLOGY: Sun in {a.sun_sign} ({a.element}/{a.modality}/ruled by {a.ruler}) | "
        f"Day: {a.day_name} = {a.day_planet} | "
        f"Next ingress: {a.next_ingress_sign} {_dt(a.next_ingress_date)}",

        f"PLANETARY ({a.day_name}): {a.day_color} | {a.day_metal} | "
        f"{a.day_stones} | Use for: {a.day_use}",

        f"SIDEREAL: JD {si.julian_date} | GMST {si.sidereal_time_hours:.2f}h | "
        f"HE {si.holocene_year}",

        f"VEDIC: {v.tithi} | Nakshatra: {v.nakshatra} | {v.paksha} paksha",

        f"SOLAR TERM: {st.current_term} | "
        f"Next: {st.next_term} in {st.days_to_next}d",

        f"CIRCADIAN: {ci.label} -- {ci.energy_phase} | "
        f"Best for: {ci.suitable_for}",

        f"MARKET: {'Trading day' if m.is_trading_day else 'Non-trading day'} | "
        f"{m.session_status} | "
        f"Quarter end in {m.days_to_quarter_end}d ({_dt(m.quarter_end_date)})",
    ]

    # Alternative calendars -- only include non-None values
    alt_parts = []
    alt = ctx.alternative
    if alt.hebrew:           alt_parts.append(f"Hebrew: {alt.hebrew}")
    if alt.islamic:          alt_parts.append(f"Islamic: {alt.islamic}")
    if alt.chinese:          alt_parts.append(f"Chinese: {alt.chinese}")
    if alt.persian:          alt_parts.append(f"Persian: {alt.persian}")
    if alt.mayan_long_count: alt_parts.append(f"Mayan: {alt.mayan_long_count}")
    if alt.ethiopian:        alt_parts.append(f"Ethiopian: {alt.ethiopian}")
    if alt_parts:
        lines.append("ALT CALENDARS: " + " | ".join(alt_parts))

    # Biorhythm -- only if configured
    bio = ctx.biorhythm
    if bio.physical_pct is not None:
        lines.append(
            f"BIORHYTHM: Physical {bio.physical_pct:+.0f} | "
            f"Emotional {bio.emotional_pct:+.0f} | "
            f"Intellectual {bio.intellectual_pct:+.0f}"
        )

    # Planets -- only if addon enabled
    if ctx.planets:
        p = ctx.planets
        lines.append(
            f"PLANETS: Mercury {p.mercury} | Venus {p.venus} | "
            f"Mars {p.mars} | Jupiter {p.jupiter} | Saturn {p.saturn}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# to_markdown -- full human-readable document
# ---------------------------------------------------------------------------

def to_markdown(ctx: TemporalContext) -> str:
    c = ctx
    g = c.gregorian
    s = c.solar
    l = c.lunar
    w = c.wheel
    a = c.astrology
    si = c.sidereal
    ci = c.circadian
    m = c.market
    v = c.vedic
    st = c.solar_terms
    alt = c.alternative
    bio = c.biorhythm

    out: list[str] = []
    add = out.append

    add("# TEMPORAL ANCHOR")
    add("")
    add(f"**Generated:** {c.generated_at.strftime('%Y-%m-%d %H:%M:%S')} {c.timezone_name}")
    add("")

    # ---- Right Now ----
    add("## Right Now")
    add(f"- **Time:** {c.generated_at.strftime('%I:%M %p').lstrip('0')} ({ci.label})")
    add(f"- **Date:** {c.generated_at.strftime('%A, %B %d, %Y')}")
    add(f"- **Timezone:** {c.timezone_name}")
    add("")

    # ---- Calendar Position ----
    add("## Calendar Position")
    add(f"- **Week:** {g.iso_week} of 52 ({g.year_pct}% through the year)")
    add(f"- **Day of year:** {g.day_of_year} of {g.days_in_year} ({g.year_pct}%)")
    add(f"- **Day of month:** {g.day_of_month} of {g.days_in_month} ({g.month_pct}% through {c.generated_at.strftime('%B')})")
    add(f"- **Day of week:** {a.day_name} ({g.week_pct}% through the week)")
    add(f"- **Quarter:** Q{g.quarter} of {c.generated_at.year}")
    add("")
    add("---")
    add("")

    # ---- Astronomy ----
    add("## Astronomy")
    add("")
    add("### Sun")
    add(f"- **Sunrise:** {s.sunrise_local}")
    add(f"- **Solar noon:** {s.solar_noon_local}")
    add(f"- **Sunset:** {s.sunset_local}")
    add(f"- **Daylight:** {s.daylight_hm} ({ci.photoperiod_trend}, {ci.minutes_vs_yesterday:+.1f}m vs yesterday)")
    add(f"- **Golden hour:** {s.golden_hour_start} - {s.golden_hour_end}")
    add("")
    add("### Moon")
    add(f"- **Phase:** {l.phase_name} (age {l.age_days}d, {l.cycle_pct}% through cycle)")
    add(f"- **Last full:** {_dt(l.prev_full)} -- **{l.full_moon_name_this_month}**")
    add(f"- **Next new:** {_dt(l.next_new)} (in {(l.next_new - c.generated_at.replace(tzinfo=None)).days}d)")
    add(f"- **Next full:** {_dt(l.next_full)} -- {l.full_moon_name_next}")
    add("")
    add("### Sidereal / Astronomical")
    add(f"- **Julian Date:** {si.julian_date}")
    add(f"- **GMST:** {si.sidereal_time_hours:.4f}h")
    add(f"- **Holocene Era:** HE {si.holocene_year}")
    add("")
    add("---")
    add("")

    # ---- Wheel of the Year ----
    add("## Wheel of the Year")
    add("")
    add(f"- **Last sabbat:** **{w.last_sabbat_name}** -- {_dt(w.last_sabbat_date)} ({w.last_sabbat_days_ago}d ago, {w.last_sabbat_type})")
    add(f"- **Next sabbat:** **{w.next_sabbat_name}** -- {_dt(w.next_sabbat_date)} (in {w.next_sabbat_days_away}d, {w.next_sabbat_type})")
    add("")
    add("### Sabbat Ladder")
    add("")
    add("| Sabbat | Date | Type |")
    add("|---|---|---|")
    for name, date_, type_ in w.ladder:
        marker = " ← next" if name == w.next_sabbat_name else ""
        add(f"| {name} | {_dt(date_)} | {type_}{marker} |")
    add("")
    add("---")
    add("")

    # ---- Astrology ----
    add("## Astrology")
    add("")
    add(f"- **Sun sign:** **{a.sun_sign}** -- {a.element}, {a.modality}, ruled by {a.ruler}")
    add(f"- **Day ruler:** **{a.day_name} = {a.day_planet}**")
    add(f"- **Next ingress:** Sun → {a.next_ingress_sign}, {_dt(a.next_ingress_date)}")
    add("")
    add(f"### {a.day_name} Correspondences ({a.day_planet} day)")
    add("")
    add(f"- **Color:** {a.day_color}")
    add(f"- **Metal:** {a.day_metal}")
    add(f"- **Stones:** {a.day_stones}")
    add(f"- **Use for:** {a.day_use}")
    add("")
    add("---")
    add("")

    # ---- Vedic ----
    add("## Vedic Panchanga")
    add("")
    add(f"- **Tithi:** {v.tithi}")
    add(f"- **Nakshatra:** {v.nakshatra}")
    add(f"- **Paksha:** {v.paksha}")
    add("")
    add("---")
    add("")

    # ---- Solar Terms ----
    add("## Chinese Solar Terms (Jieqi)")
    add("")
    add(f"- **Current:** {st.current_term} (since {_dt(st.current_term_start)})")
    add(f"- **Next:** {st.next_term} on {_dt(st.next_term_date)} (in {st.days_to_next}d)")
    add("")
    add("---")
    add("")

    # ---- Circadian ----
    add("## Circadian / Biological")
    add("")
    add(f"- **Phase:** {ci.label}")
    add(f"- **Energy:** {ci.energy_phase}")
    add(f"- **Best for:** {ci.suitable_for}")
    add(f"- **Photoperiod:** {ci.photoperiod_trend} ({ci.minutes_vs_yesterday:+.1f}m vs yesterday)")
    add("")

    # ---- Biorhythm (optional) ----
    if bio.physical_pct is not None:
        add("### Biorhythm Cycles")
        add("")
        add(f"- **Physical (23d):** {bio.physical_pct:+.1f}")
        add(f"- **Emotional (28d):** {bio.emotional_pct:+.1f}")
        add(f"- **Intellectual (33d):** {bio.intellectual_pct:+.1f}")
        add("")

    add("---")
    add("")

    # ---- Market ----
    add("## Market Calendar")
    add("")
    add(f"- **Trading day:** {'Yes' if m.is_trading_day else 'No'}")
    add(f"- **Session:** {m.session_status}")
    add(f"- **Quarter end:** {_dt(m.quarter_end_date)} (in {m.days_to_quarter_end}d)")
    add("")
    add("---")
    add("")

    # ---- Alternative Calendars ----
    add("## Alternative Calendars")
    add("")
    if alt.hebrew:           add(f"- **Hebrew:** {alt.hebrew}")
    if alt.islamic:          add(f"- **Islamic Hijri:** {alt.islamic}")
    if alt.chinese:          add(f"- **Chinese lunisolar:** {alt.chinese}")
    if alt.persian:          add(f"- **Persian (Jalali):** {alt.persian}")
    if alt.mayan_long_count: add(f"- **Mayan Long Count:** {alt.mayan_long_count}")
    if alt.ethiopian:        add(f"- **Ethiopian:** {alt.ethiopian}")
    if alt.coptic:           add(f"- **Coptic:** {alt.coptic}")
    if alt.julian:           add(f"- **Julian calendar:** {alt.julian}")
    if not any([alt.hebrew, alt.islamic, alt.chinese, alt.persian,
                alt.mayan_long_count, alt.ethiopian, alt.coptic, alt.julian]):
        add("*Install convertdate for alternative calendars: `pip install convertdate`*")
    add("")

    # ---- Planets (optional) ----
    if ctx.planets:
        p = ctx.planets
        add("---")
        add("")
        add("## Planetary Positions (skyfield)")
        add("")
        add(f"- **Mercury:** {p.mercury}")
        add(f"- **Venus:** {p.venus}")
        add(f"- **Mars:** {p.mars}")
        add(f"- **Jupiter:** {p.jupiter}")
        add(f"- **Saturn:** {p.saturn}")
        add("")

    add("---")
    add("")
    add("*Generated by 24K Labs Clock Module*")
    add("")

    return "\n".join(out)
