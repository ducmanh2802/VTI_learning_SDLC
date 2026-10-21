"""Money helpers (property based)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from analytics.common.money import (
    MoneyError,
    format_price,
    format_vnd,
    parse_price,
    parse_vnd,
)


@given(st.integers(min_value=0, max_value=10**15))
def test_parse_vnd_keeps_integers(amount: int) -> None:
    assert parse_vnd(amount) == amount
    assert parse_vnd(str(amount)) == amount
    assert isinstance(parse_vnd(amount), int)


@given(st.integers(min_value=0, max_value=10**12))
def test_parse_vnd_round_trips_through_a_string(amount: int) -> None:
    assert parse_vnd(f"{amount:,}".replace(",", "")) == amount


@given(st.integers(min_value=-(10**12), max_value=10**12))
def test_parse_vnd_accepts_negative_amounts(amount: int) -> None:
    assert parse_vnd(amount) == amount
    assert parse_vnd(str(amount)) == amount


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_parse_vnd_refuses_floats(value: float) -> None:
    with pytest.raises(MoneyError):
        parse_vnd(value)


@pytest.mark.parametrize("value", ["", "abc", "12.5", "1 000", "12,5", "1e5"])
def test_parse_vnd_refuses_invalid_strings(value: str) -> None:
    with pytest.raises(MoneyError):
        parse_vnd(value)


@given(st.decimals(min_value=0, max_value=10**9, places=2))
def test_parse_price_keeps_two_decimals(value: Decimal) -> None:
    parsed = parse_price(value)

    assert isinstance(parsed, Decimal)
    assert parsed == value
    assert parsed.as_tuple().exponent == -2


@given(st.integers(min_value=0, max_value=10**9))
def test_parse_price_accepts_integers(value: int) -> None:
    assert parse_price(value) == Decimal(value).quantize(Decimal("0.01"))
    assert parse_price(str(value)) == Decimal(value).quantize(Decimal("0.01"))


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_parse_price_refuses_floats(value: float) -> None:
    with pytest.raises(MoneyError):
        parse_price(value)


@pytest.mark.parametrize("value", ["", "abc", "1.234"])
def test_parse_price_refuses_invalid_values(value: str) -> None:
    with pytest.raises(MoneyError):
        parse_price(value)


@given(st.integers(min_value=0, max_value=10**9))
def test_format_vnd_uses_dots_as_thousand_separators(amount: int) -> None:
    formatted = format_vnd(amount)

    assert "," not in formatted
    assert formatted.replace(".", "").isdigit()


@given(st.decimals(min_value=0, max_value=10**6, places=2))
def test_format_price_uses_the_vietnamese_conventions(value: Decimal) -> None:
    formatted = format_price(value)

    assert formatted.count(",") == 1
    integer_part, decimal_part = formatted.split(",")
    assert len(decimal_part) == 2
    assert integer_part.replace(".", "").isdigit()
