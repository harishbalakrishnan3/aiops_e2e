"""Shared step/time parsing utility functions.

Used by both features/steps/ and scripts/ to avoid code duplication.
"""

import re


_MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_step_to_seconds(step_str: str) -> int:
    """Convert Prometheus step string (e.g., '5m', '1h', '30s') to seconds.

    Args:
        step_str: Step size string like '5m', '1h', '30s', '1d'

    Returns:
        int: Step size in seconds

    Raises:
        ValueError: If format is invalid
    """
    match = re.match(r"^(\d+)([smhd])$", str(step_str).lower())
    if not match:
        raise ValueError(f"Invalid step format: {step_str}")
    value, unit = int(match.group(1)), match.group(2)
    return value * _MULTIPLIERS[unit]


def parse_step_to_minutes(step_size_str) -> int:
    """Parse step size string (e.g., '5m', '15m', '1h') to minutes.

    Also accepts a bare integer (treated as minutes).

    Args:
        step_size_str: Step size string like '5m', '15m', '1h', '30s' or integer

    Returns:
        int: Step size in minutes

    Raises:
        ValueError: If format is invalid or result is less than 1 minute
    """
    # If it's already an integer, return it
    if isinstance(step_size_str, int):
        return step_size_str

    # Try to parse as integer directly
    try:
        return int(step_size_str)
    except ValueError:
        pass

    seconds = parse_step_to_seconds(step_size_str)
    minutes = seconds / 60.0

    if minutes < 1:
        raise ValueError(
            f"Step size must be at least 1 minute, got {minutes} minutes from '{step_size_str}'"
        )

    return int(minutes)
