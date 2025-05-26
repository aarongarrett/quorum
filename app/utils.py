from __future__ import annotations

from datetime import datetime


def strftime(value: datetime | str, format: str = "%B %d, %Y %I:%M%p") -> str:
    """Format a datetime object or string into a human-readable format.

    Args:
        value: Either a datetime object or a string that can be parsed into a datetime
        format: The strftime format string to use for formatting

    Returns:
        str: The formatted date/time string
    """
    if value is None:
        return ""

    # Convert string to datetime if needed
    if isinstance(value, str):
        value = datetime.fromisoformat(value)

    # Format the date and time
    formatted = value.strftime(format)
    # Remove leading zero from hour if present
    if " 0" in formatted:
        formatted = formatted.replace(" 0", " ")
    # Convert AM/PM to lowercase
    formatted = formatted.replace("AM", "am").replace("PM", "pm")
    return formatted
