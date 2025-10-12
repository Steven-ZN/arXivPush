# utils.py
from datetime import datetime, timedelta
from dateutil import tz

def now_in_tz(tzname: str):
    return datetime.now(tz.gettz(tzname))

def last_window_start(tzname: str, hours: int):
    t = now_in_tz(tzname)
    return t - timedelta(hours=hours)

def fmt_period(dt):
    return dt.strftime("%Y-%m-%d_%p").upper()  # e.g. 2025-10-09_AM / _PM