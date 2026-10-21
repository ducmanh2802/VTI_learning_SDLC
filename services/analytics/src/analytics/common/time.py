"""Time helpers.

`Asia/Ho_Chi_Minh` is the trading timezone of the product. Domain code must
use these helpers instead of calling `datetime.now()` directly (AGENTS.md 7).
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

TRADING_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def utcnow() -> datetime:
    """Return the current instant in UTC, timezone aware."""
    return datetime.now(UTC)


def to_trading_tz(moment: datetime) -> datetime:
    """Convert an instant to the trading timezone.

    A naive datetime is refused: `astimezone` would read it in the host's
    local timezone, which differs between a dev machine and a container.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("a naive datetime has no instant; attach a timezone first")
    return moment.astimezone(TRADING_TZ)


def trading_date(moment: datetime | None = None) -> date:
    """Return the trading date of an instant, defaulting to now."""
    return to_trading_tz(moment or utcnow()).date()
