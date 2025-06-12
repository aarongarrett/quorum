import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import qrcode
from qrcode.image.svg import SvgImage


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("All times must be timezone-aware (include tzinfo)")
    # Convert any zone into UTC
    return dt.astimezone(timezone.utc)


def make_pronounceable(length: int = 8) -> str:
    """Generate a pronounceable token of the specified length

    The token alternates between consonants and vowels to make it
    easier to read and say.

    Args:
        length: The length of the token to generate

    Returns:
        str: A pronounceable token
    """
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    vowels = "AEIOU"
    token = []
    for i in range(length):
        token.append(secrets.choice(vowels) if i % 2 else secrets.choice(consonants))
    return "".join(token)


def generate_qr_code(data: str, svg=True) -> io.BytesIO:
    """Generate a QR code as a BytesIO object.

    Args:
        data: The data to encode in the QR code

    Returns:
        io.BytesIO: A BytesIO object containing the QR code image in SVG format
    """
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create an in-memory image
    if svg:
        img = qr.make_image(
            image_factory=SvgImage, fill_color="black", back_color="white"
        )
    else:
        img = qr.make_image(fill_color="black", back_color="white")
    # Save to a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer


def is_available(
    start_time: Union[datetime, str],
    end_time: Union[datetime, str],
    current_time: Optional[datetime] = None,
) -> bool:
    """Check if a current time (or now) is between start time and end time.

    Args:
        start_time: datetime or ISO format string
        end_time: datetime or ISO format string
        current_time: Optional current time for testing (defaults to now)

    Returns:
        bool: True if current time is between start time and end time
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    current_utc = to_utc(current_time)

    # Convert string times to datetime objects if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    start_utc = to_utc(start_time)
    end_utc = to_utc(end_time)

    # Allow check-in 15 minutes before and 15 minutes after start
    checkin_utc = start_utc - timedelta(minutes=15)

    # Meeting is available if current time is within the check-in window
    # and before the meeting end time
    return checkin_utc <= current_utc <= end_utc
