from datetime import datetime

import pytest

from app.utils import strftime


def test_strftime_with_datetime():
    """Test strftime with a datetime object input."""
    # Create a specific datetime (2023-01-15 14:30:00)
    dt = datetime(2023, 1, 15, 14, 30, 0)

    # Test with default format
    assert strftime(dt) == "January 15, 2023 2:30pm"

    # Test with custom format
    assert strftime(dt, "%Y-%m-%d") == "2023-01-15"
    assert strftime(dt, "%I:%M %p") == "2:30 pm"


def test_strftime_with_iso_string():
    """Test strftime with an ISO format string input."""
    iso_str = "2023-01-15T14:30:00"

    # Test with default format
    assert strftime(iso_str) == "January 15, 2023 2:30pm"

    # Test with custom format
    assert strftime(iso_str, "%A, %B %d, %Y") == "Sunday, January 15, 2023"


def test_strftime_edge_cases():
    """Test edge cases for strftime."""
    # Test with None input
    assert strftime(None) == ""

    # Test with empty string
    assert strftime("") == ""

    # Test with midnight
    midnight = datetime(2023, 1, 1, 0, 0, 0)
    assert strftime(midnight, "%I:%M%p") == "12:00am"

    # Test with noon
    noon = datetime(2023, 1, 1, 12, 0, 0)
    assert strftime(noon, "%I:%M%p") == "12:00pm"


def test_strftime_leading_zeros():
    """Test that leading zeros are removed from hours."""
    # Test with single-digit hour (should remove leading zero)
    dt = datetime(2023, 1, 1, 9, 15, 0)
    assert strftime(dt, "%I:%M%p") == "9:15am"

    # Test with double-digit hour (should not modify)
    dt = datetime(2023, 1, 1, 14, 15, 0)
    assert strftime(dt, "%I:%M%p") == "2:15pm"


def test_strftime_am_pm_lowercase():
    """Test that AM/PM are converted to lowercase."""
    # Test AM
    dt_am = datetime(2023, 1, 1, 9, 0, 0)
    assert strftime(dt_am, "%I:%M%p").endswith("am")

    # Test PM
    dt_pm = datetime(2023, 1, 1, 15, 0, 0)
    assert strftime(dt_pm, "%I:%M%p").endswith("pm")


def test_strftime_custom_formats():
    """Test various custom format strings."""
    dt = datetime(2023, 12, 31, 23, 59, 59)

    # Date only
    assert strftime(dt, "%Y-%m-%d") == "2023-12-31"

    # Time only
    assert strftime(dt, "%H:%M:%S") == "23:59:59"

    # Day of week
    assert strftime(dt, "%A") == "Sunday"

    # Month name and day
    assert strftime(dt, "%B %d") == "December 31"


def test_strftime_invalid_input():
    """Test handling of invalid input."""
    # Test with invalid date string
    with pytest.raises(ValueError):
        strftime("not-a-date")

    # Test with unsupported type
    with pytest.raises(AttributeError):
        strftime(123)  # type: ignore
