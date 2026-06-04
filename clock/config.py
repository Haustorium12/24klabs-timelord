"""
clock.config
============
All configurable values in one place.
Nothing else hardcodes paths, ports, or model names.

Override any value via environment variable:
    CLOCK_TZ=America/Chicago
    CLOCK_PORT=7654
    CLOCK_MODEL=llama3.2:3b
    CLOCK_OUTPUT_DIR=C:/ProgramData/24klabs/clock
    CLOCK_LAT=40.0
    CLOCK_LON=-75.0
    CLOCK_PLANETS=1          (enable skyfield addon)
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed -- env vars must be set externally


# ---------------------------------------------------------------------------
# Timezone -- OS-detected first, env override second, fallback third
# ---------------------------------------------------------------------------

def _resolve_timezone() -> ZoneInfo:
    """
    Resolution order:
      1. CLOCK_TZ env var (explicit user override)
      2. System timezone via tzlocal-style key lookup (Windows registry / /etc/localtime)
      3. Hard fallback: America/New_York
    """
    # 1. Env override
    env_tz = os.environ.get("CLOCK_TZ", "").strip()
    if env_tz:
        try:
            return ZoneInfo(env_tz)
        except ZoneInfoNotFoundError:
            pass  # fall through

    # 2. OS detection
    #    On Windows: reads HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation
    #    On Linux/Mac: reads /etc/localtime symlink
    try:
        import sys
        if sys.platform == "win32":
            import winreg  # type: ignore[import]
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
            )
            win_tz, _ = winreg.QueryValueEx(key, "TimeZoneKeyName")
            winreg.CloseKey(key)
            # Windows tz names map to IANA -- try direct, then common mappings
            WINDOWS_TO_IANA = {
                "Eastern Standard Time":  "America/New_York",
                "Eastern Daylight Time":  "America/New_York",
                "Central Standard Time":  "America/Chicago",
                "Mountain Standard Time": "America/Denver",
                "Pacific Standard Time":  "America/Los_Angeles",
                "UTC":                    "UTC",
            }
            iana = WINDOWS_TO_IANA.get(win_tz, win_tz)
            return ZoneInfo(iana)
        else:
            # Linux / Mac -- /etc/localtime is a symlink into zoneinfo
            lt = Path("/etc/localtime").resolve()
            # Extract IANA key from path  e.g. .../zoneinfo/America/New_York
            parts = lt.parts
            if "zoneinfo" in parts:
                idx = parts.index("zoneinfo")
                iana = "/".join(parts[idx + 1:])
                return ZoneInfo(iana)
    except Exception:
        pass  # fall through to hard fallback

    # 3. Hard fallback
    return ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

TIMEZONE: ZoneInfo = _resolve_timezone()

# Geographic coordinates -- used for solar calculations
LAT: float = float(os.environ.get("CLOCK_LAT", "40.0"))   # Philadelphia corridor
LON: float = float(os.environ.get("CLOCK_LON", "-75.0"))

# HTTP API
API_HOST: str  = os.environ.get("CLOCK_HOST", "127.0.0.1")
API_PORT: int  = int(os.environ.get("CLOCK_PORT", "7777"))

# File output directory -- OneDrive is OFF LIMITS
OUTPUT_DIR: Path = Path(
    os.environ.get("CLOCK_OUTPUT_DIR", r"C:\ProgramData\24klabs\clock")
)

# Ollama
OLLAMA_BASE: str    = os.environ.get("CLOCK_OLLAMA_BASE", "http://localhost:11434")
TIMELORD_MODEL: str = os.environ.get("CLOCK_MODEL", "llama3.2:3b")

# Feature flags
PLANETS_ENABLED: bool = os.environ.get("CLOCK_PLANETS", "0") == "1"

# File refresh interval (seconds) -- how often writer loop updates the snapshot
FILE_REFRESH_INTERVAL: int = int(os.environ.get("CLOCK_REFRESH", "60"))

# Profiles directory -- one JSON file per identity, gitignored.
# profiles/{name}.json  contains: name, token, schedule[]
# Remote callers present X-Profile + X-Profile-Token headers to get
# personalized circadian context. Unknown/missing token -> generic fallback.
PROFILES_DIR: Path = Path(
    os.environ.get(
        "CLOCK_PROFILES_DIR",
        str(Path(__file__).parent.parent / "profiles"),
    )
)
