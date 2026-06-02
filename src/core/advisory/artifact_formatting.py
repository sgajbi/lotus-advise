from decimal import Decimal


def decimal_to_str(value: Decimal) -> str:
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def quantized_weight_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")
