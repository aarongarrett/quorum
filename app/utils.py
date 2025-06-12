from __future__ import annotations

import re
from datetime import datetime


def strftime(value: datetime | str, format: str = "%B %d, %Y %I:%M%p") -> str:
    """Format a datetime object or string into a human-readable format.

    Args:
        value: A datetime object or a string that can be parsed into a datetime
        format: The strftime format string to use for formatting

    Returns:
        str: The formatted date/time string
    """
    if value is None or value == "":
        return ""

    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    formatted = value.strftime(format)
    formatted = re.sub(r"(?<=\s)0|^0", "", formatted)
    # Convert AM/PM to lowercase
    formatted = formatted.replace("AM", "am").replace("PM", "pm")
    return formatted
