"""General utility functions."""
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.constants import MEETING_CODE_LENGTH


def make_pronounceable(length: int = MEETING_CODE_LENGTH) -> str:
    """Generate a pronounceable code using consonant-vowel pattern."""
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    vowels = "AEIOU"

    code = ""
    for i in range(length):
        if i % 2 == 0:
            code += random.choice(consonants)
        else:
            code += random.choice(vowels)

    return code


def is_available(start_time: datetime, end_time: datetime, buffer_minutes: int = 15) -> bool:
    """
    Check if a meeting is currently available for check-in/voting.

    Args:
        start_time: Meeting start time (timezone-aware or naive, assumed UTC if naive)
        end_time: Meeting end time (timezone-aware or naive, assumed UTC if naive)
        buffer_minutes: Minutes before start to allow check-in

    Returns:
        bool: True if meeting is currently available
    """
    now = datetime.now(timezone.utc)

    # Ensure start_time and end_time are timezone-aware
    start_time = to_utc(start_time)
    end_time = to_utc(end_time)

    start_buffer = start_time - timedelta(minutes=buffer_minutes)

    return start_buffer <= now <= end_time


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC timezone."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_timezone(dt: datetime, tz: ZoneInfo) -> datetime:
    """Convert datetime to specified timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)
