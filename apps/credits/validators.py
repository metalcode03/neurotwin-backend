"""
Input validation utilities for credit-related API requests.

Centralised helpers that enforce enum membership, positive-integer
constraints, and date-range sanity checks.

Requirements: 22.9
"""

from datetime import datetime
from rest_framework import serializers
from apps.credits.enums import BrainMode, OperationType


def validate_brain_mode(value: str) -> str:
    """
    Validate that *value* is a recognised BrainMode enum member.

    Raises serializers.ValidationError on failure.
    """
    if not BrainMode.is_valid_mode(value):
        raise serializers.ValidationError(
            f"Invalid brain_mode '{value}'. "
            f"Must be one of: {', '.join(m.value for m in BrainMode)}"
        )
    return value


def validate_operation_type(value: str) -> str:
    """
    Validate that *value* is a recognised OperationType enum member.

    Raises serializers.ValidationError on failure.
    """
    if not OperationType.is_valid_type(value):
        raise serializers.ValidationError(
            f"Invalid operation_type '{value}'. "
            f"Must be one of: {', '.join(t.value for t in OperationType)}"
        )
    return value


def validate_positive_integer(value, field_name: str = 'value') -> int:
    """
    Validate that *value* is a positive integer.

    Raises serializers.ValidationError on failure.
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise serializers.ValidationError(
            f"{field_name} must be a valid integer"
        )
    if int_value <= 0:
        raise serializers.ValidationError(
            f"{field_name} must be a positive integer"
        )
    return int_value


def validate_date_range(start_date, end_date):
    """
    Validate that *start_date* ≤ *end_date*.

    Both arguments may be ``None`` (no filter).
    Raises serializers.ValidationError if dates are reversed.
    """
    if start_date and end_date:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)
        if start_date > end_date:
            raise serializers.ValidationError(
                "start_date must be earlier than or equal to end_date"
            )
    return start_date, end_date
