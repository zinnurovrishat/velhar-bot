"""Simple full-moon proximity check (no external deps)."""
import math
from datetime import datetime, timezone


# Known full moon reference: 2000-01-21 04:41 UTC (J2000 era)
_KNOWN_FULLMOON_JD = 2451564.6951
_LUNAR_CYCLE = 29.53058770  # days


def _julian_day(dt: datetime) -> float:
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    frac = (dt.hour - 12) / 24 + dt.minute / 1440 + dt.second / 86400
    return jdn + frac


def days_to_fullmoon(dt: datetime | None = None) -> float:
    """Return signed days to nearest full moon (negative = past, positive = future)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    jd = _julian_day(dt)
    delta = jd - _KNOWN_FULLMOON_JD
    cycles = delta / _LUNAR_CYCLE
    phase = (cycles % 1 + 1) % 1  # 0..1, 0=new, 0.5=full
    # distance from full moon phase (0.5)
    dist_from_full = phase - 0.5
    if dist_from_full > 0.5:
        dist_from_full -= 1.0
    elif dist_from_full < -0.5:
        dist_from_full += 1.0
    return dist_from_full * _LUNAR_CYCLE


def is_near_fullmoon(tolerance_days: float = 2.0) -> bool:
    return abs(days_to_fullmoon()) <= tolerance_days
