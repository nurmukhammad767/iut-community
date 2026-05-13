"""Period start times for IUT lessons (Asia/Tashkent).

Edit PERIOD_START_TIMES if the real schedule differs — the Celery reminder
task computes "lesson starts in 15 min" off this map.
"""
from datetime import datetime, time, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore


TZ = ZoneInfo("Asia/Tashkent")


# Period number -> start time (HH, MM) in Asia/Tashkent local time.
# Defaults derived from the user-provided schedule and extrapolated at
# 30-minute intervals; tweak as needed.
PERIOD_START_TIMES = {
    "1": time(9, 30),
    "2": time(10, 0),
    "3": time(10, 30),
    "4": time(11, 0),
    "5": time(11, 30),
    "6": time(12, 0),
    "7": time(12, 30),
    "8": time(13, 0),
    "9": time(13, 30),
}


# day_mask index (0..4) -> Python weekday (Mon=0)
_MASK_TO_WEEKDAY = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}


def period_start_dt(period: str, on_date) -> Optional[datetime]:
    """Return the timezone-aware datetime when `period` starts on `on_date`."""
    t = PERIOD_START_TIMES.get(str(period))
    if t is None:
        return None
    return datetime.combine(on_date, t).replace(tzinfo=TZ)


def lesson_today_at(period: str, now: datetime) -> Optional[datetime]:
    """Datetime today (Tashkent) when `period` starts; None if unknown."""
    local = now.astimezone(TZ)
    return period_start_dt(period, local.date())


def session_runs_on(day_mask: str, weekday: int) -> bool:
    """True if `day_mask` (e.g. '10100') includes `weekday` (Mon=0..Fri=4)."""
    if weekday > 4 or weekday < 0:
        return False
    return len(day_mask) > weekday and day_mask[weekday] == "1"
