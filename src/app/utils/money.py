from __future__ import annotations

from decimal import Decimal
import re


_MONEY_RE = re.compile(
    r"""(?x)
    (?P<sign>[+-])?\s*
    (?P<int>[\d\s]+)
    (?:
        [\.,](?P<frac>\d{1,2})
    )?
    \s*(?:₽|RUB|руб\.?|р\.)?
    """
)


def parse_money_to_decimal(value: str) -> Decimal:
    """Parse money strings like '-1 599.00 ₽' or '126 191,00 ₽' into Decimal."""
    m = _MONEY_RE.search(value.strip())
    if not m:
        raise ValueError(f"Cannot parse money: {value!r}")
    sign = -1 if (m.group("sign") == "-") else 1
    integer = m.group("int").replace(" ", "")
    frac = (m.group("frac") or "0").ljust(2, "0")[:2]
    return Decimal(sign) * (Decimal(integer) + (Decimal(frac) / Decimal(100)))


def decimal_to_str(d: Decimal) -> str:
    # Keep 2 decimal places in string JSON output
    return f"{d:.2f}"
