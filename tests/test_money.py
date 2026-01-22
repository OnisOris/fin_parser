from decimal import Decimal
import pytest

from app.utils.money import parse_money_to_decimal


@pytest.mark.parametrize(
    "s, expected",
    [
        ("-1 599.00 ₽", Decimal("-1599.00")),
        ("+65 250.00 ₽", Decimal("65250.00")),
        ("126 191,00 ₽", Decimal("126191.00")),
        ("-86 342,67 ₽", Decimal("-86342.67")),
    ],
)
def test_parse_money_to_decimal(s: str, expected: Decimal) -> None:
    assert parse_money_to_decimal(s) == expected
