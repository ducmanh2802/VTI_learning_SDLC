"""Money helpers.

VND amounts are integers, prices are decimals with at most two decimals.
Floating point values are refused: they would silently lose precision
(AGENTS.md 2.5).
"""

import re
from decimal import Decimal, InvalidOperation

PRICE_QUANTUM = Decimal("0.01")
_VND_PATTERN = re.compile(r"^[+-]?\d+$")


class MoneyError(ValueError):
    """Raised when a value cannot be parsed as money or as a price."""


def parse_vnd(raw: str | int | Decimal) -> int:
    """Parse a VND amount into an integer.

    Accepts an integer, a decimal without fraction or a string of digits.
    Floats are refused: a VND amount is never a floating point number.
    Separators are refused too, so that no amount is read in the wrong unit.
    """
    if isinstance(raw, bool):
        raise MoneyError("a boolean is not a VND amount")
    if isinstance(raw, float):
        raise MoneyError("a float is not a VND amount; use an integer or a string")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, Decimal):
        if not raw.is_finite() or raw != raw.to_integral_value():
            raise MoneyError(f"{raw} is not a whole VND amount")
        return int(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not _VND_PATTERN.match(text):
            raise MoneyError(f"{raw!r} is not a VND amount")
        return int(text)
    raise MoneyError(f"{type(raw).__name__} is not a VND amount")


def parse_price(raw: str | int | Decimal) -> Decimal:
    """Parse a price into a decimal with at most two decimals.

    Floats are refused, and a value with more than two decimals is rejected
    instead of being silently rounded. A string uses the dot as the decimal
    separator and carries no thousand separator.
    """
    if isinstance(raw, bool):
        raise MoneyError("a boolean is not a price")
    if isinstance(raw, float):
        raise MoneyError("a float is not a price; use a string, an integer or a Decimal")
    if isinstance(raw, int):
        value = Decimal(raw)
    elif isinstance(raw, Decimal):
        value = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise MoneyError("an empty string is not a price")
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise MoneyError(f"{raw!r} is not a price") from exc
    else:
        raise MoneyError(f"{type(raw).__name__} is not a price")

    if not value.is_finite():
        raise MoneyError(f"{raw!r} is not a finite price")
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and -exponent > 2:
        raise MoneyError(f"{raw!r} has more than two decimals")
    return value.quantize(PRICE_QUANTUM)


def format_vnd(amount: int) -> str:
    """Format a VND amount with dots as thousand separators, e.g. `25.350.000`."""
    return f"{amount:,}".replace(",", ".")


def format_price(price: Decimal) -> str:
    """Format a price for display, e.g. `25.350,00`.

    This is the Vietnamese display convention; `parse_price` reads the plain
    machine format instead.
    """
    text = f"{price.quantize(PRICE_QUANTUM):,.2f}"
    integer_part, _, decimal_part = text.partition(".")
    return f"{integer_part.replace(',', '.')},{decimal_part}"
