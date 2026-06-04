from decimal import Decimal
from typing import Dict, Optional, TypeVar

_GROUP_CONSTRAINT_KEY_FORMAT = "<attribute_key>:<attribute_value>"
GroupConstraintT = TypeVar("GroupConstraintT")


def validate_group_constraint_keys(
    group_constraints: Dict[str, GroupConstraintT],
) -> Dict[str, GroupConstraintT]:
    for key in group_constraints:
        if key.count(":") != 1:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
        attribute_key, attribute_value = key.split(":", 1)
        if not attribute_key or not attribute_value:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
    return group_constraints


def validate_optional_ratio_between_zero_and_one(
    value: Optional[Decimal], *, field_name: str
) -> Optional[Decimal]:
    if value is None:
        return value
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def validate_non_negative_amounts_by_currency(
    amounts_by_currency: Dict[str, Decimal], *, field_name: str
) -> Dict[str, Decimal]:
    for currency, amount in amounts_by_currency.items():
        if not currency:
            raise ValueError(f"{field_name} keys must be non-empty currency codes")
        if amount < Decimal("0"):
            raise ValueError(f"{field_name} values must be non-negative")
    return amounts_by_currency


__all__ = [
    "validate_group_constraint_keys",
    "validate_non_negative_amounts_by_currency",
    "validate_optional_ratio_between_zero_and_one",
]
