# app/services/wastage.py
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

from app.errors import ValidationFailure


def expected_fabric(target_qty: int, std_yards: Union[Decimal, float, str]) -> Decimal:
    """Calculates total expected fabric required for the target quantity."""
    return Decimal(str(target_qty)) * Decimal(str(std_yards))


def wastage_pct(
    actual_yards: Union[Decimal, float, str],
    expected_yards: Union[Decimal, float, str],
) -> Decimal:
    """Calculates fabric wastage percentage rounded to 2 decimal places using HALF_UP rounding."""
    actual = Decimal(str(actual_yards))
    expected = Decimal(str(expected_yards))

    if expected <= Decimal("0"):
        raise ValidationFailure("expected fabric must be above zero")

    raw = ((actual - expected) / expected) * Decimal("100")
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def exceeds_cap(
    pct: Union[Decimal, float, str],
    cap: Union[Decimal, float, str],
) -> bool:
    """Checks whether the wastage percentage exceeds the allowed threshold cap."""
    return Decimal(str(pct)) > Decimal(str(cap))