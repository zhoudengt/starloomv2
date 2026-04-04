"""Business calendar day in Asia/Shanghai (北京时间) for daily fortune and related APIs."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def fortune_date_beijing(now: datetime | None = None) -> date:
    """Today's date in Beijing, for keys like `daily:{sign}:{YYYY-MM-DD}`."""
    if now is None:
        now = datetime.now(BEIJING_TZ)
    else:
        if now.tzinfo is None:
            now = now.replace(tzinfo=BEIJING_TZ)
        else:
            now = now.astimezone(BEIJING_TZ)
    return now.date()
