from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    text = str(value).replace(",", "").replace("￥", "").strip()
    if text in {"", "-"}:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def to_int(value: Any) -> int:
    return int(to_decimal(value))


def to_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()

