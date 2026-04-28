"""
Formatting helper functions for Django admin display methods.

Provides consistent formatting for credit amounts, currency values,
and timestamps across all admin list views.
"""

from datetime import datetime


def format_credits(amount: int) -> str:
    """Format credit amount with comma-separated thousands.

    Args:
        amount: The credit amount to format.

    Returns:
        Comma-separated string (e.g., 1000 → "1,000").
    """
    return f"{amount:,}"


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format a monetary value with currency symbol prefix.

    Args:
        amount: The monetary value to format.
        symbol: Currency symbol to prepend (default: "$").

    Returns:
        Formatted currency string (e.g., 9.99 → "$9.99").
    """
    return f"{symbol}{amount:,.2f}"


def format_timestamp(dt: datetime) -> str:
    """Format a datetime as a human-readable timestamp.

    Args:
        dt: The datetime object to format.

    Returns:
        Human-readable string (e.g., "Jan 15, 2025 at 14:30").
    """
    return dt.strftime("%b %d, %Y at %H:%M")
