from __future__ import annotations

from typing import Literal

from pydantic import ValidationError


def fmu_discriminator(
    value: dict,
) -> Literal[
    "FMUAggregation",
    "FMURealization",
    "FMUCase",
]:
    """
    Discriminate the type of FMU based on the fields present in the value.

    This function determines the type of an FMU object by checking the presence
    of specific fields ('aggregation' and 'realization') in the given value.
    It returns a string literal indicating the determined type of the FMU.

    - If both 'aggregation' and 'realization' fields are present,
        it raises a ValidationError.
    - If 'aggregation' is present, it returns 'FMUAggregation'.
    - If 'realization' is present, it returns 'FMURealization'.
    - If neither is present, it defaults to 'FMUCase'.
    """

    if not isinstance(value, dict):
        raise ValidationError("Input value must be a dictionary.")

    if "aggregation" in value and "realization" in value:
        raise ValidationError(
            "Value cannot have both 'aggregation' and 'realization' "
            "fields. It must exclusively be either an 'FMUAggregation' "
            "or an 'FMURealization'."
        )

    if "aggregation" in value:
        return "FMUAggregation"

    if "realization" in value:
        return "FMURealization"

    return "FMUCase"
