"""Time helpers (property based)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from analytics.common.time import TRADING_TZ, to_trading_tz, trading_date, utcnow


def test_the_trading_timezone_is_ho_chi_minh() -> None:
    assert TRADING_TZ.key == "Asia/Ho_Chi_Minh"


def test_utcnow_is_timezone_aware() -> None:
    now = utcnow()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


@given(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)))
def test_to_trading_tz_keeps_the_instant(moment: datetime) -> None:
    aware = moment.replace(tzinfo=UTC)
    converted = to_trading_tz(aware)

    assert converted == aware
    assert converted.utcoffset() == timedelta(hours=7)


@given(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)))
def test_trading_date_uses_the_trading_timezone(moment: datetime) -> None:
    aware = moment.replace(tzinfo=UTC)

    assert trading_date(aware) == aware.astimezone(TRADING_TZ).date()
    assert isinstance(trading_date(aware), date)


def test_trading_date_defaults_to_now() -> None:
    assert trading_date() == to_trading_tz(utcnow()).date()


def test_trading_date_rolls_over_at_midnight_in_vietnam() -> None:
    # 17:00 UTC is midnight in Vietnam (UTC+7).
    moment = datetime(2026, 10, 20, 17, 0, tzinfo=UTC)

    assert trading_date(moment) == date(2026, 10, 21)


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError):
        to_trading_tz(datetime(2026, 10, 20, 17, 0))
    with pytest.raises(ValueError):
        trading_date(datetime(2026, 10, 20, 17, 0))


@pytest.mark.parametrize("value", ["2026-10-20", 20261020])
def test_invalid_inputs_are_rejected(value: object) -> None:
    with pytest.raises((TypeError, AttributeError, ValueError)):
        to_trading_tz(value)  # type: ignore[arg-type]
