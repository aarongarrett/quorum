"""Input sanitization utilities."""
import html
import re
from typing import Optional


# Maximum length constraints for security
MAX_MEETING_CODE_LENGTH = 50  # Generous limit for meeting codes
MAX_POLL_NAME_LENGTH = 200    # Reasonable limit for poll names
MAX_TOKEN_LENGTH = 100        # Tokens should be ~43 chars for URL-safe base64


def sanitize_text(text: str, max_length: Optional[int] = None, strip_html: bool = True) -> str:
    """
    Sanitize text input to prevent XSS attacks.

    Note: This function strips HTML tags and normalizes whitespace, but does NOT
    escape HTML entities because React automatically escapes output when rendering.
    Double-escaping would cause entities to display literally (e.g., "&lt;" instead of "<").

    Args:
        text: The input text to sanitize
        max_length: Optional maximum length to enforce
        strip_html: Whether to strip HTML tags (default True)

    Returns:
        Sanitized text with HTML tags removed and whitespace normalized

    Raises:
        ValueError: If text exceeds max_length or contains dangerous patterns
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # Strip leading/trailing whitespace
    sanitized = text.strip()

    # Enforce maximum length before processing to prevent length-based attacks
    if max_length and len(sanitized) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")

    # Strip HTML tags completely if requested (prevents injection entirely)
    if strip_html:
        # Remove all HTML tags (simple approach - removes anything between < and >)
        sanitized = re.sub(r'<[^>]*>', '', sanitized)

    # Reject inputs that still contain HTML-like patterns after stripping
    # This catches malformed tags or encoded attacks
    if '<' in sanitized or '>' in sanitized:
        raise ValueError("Input contains invalid HTML-like patterns")

    # Normalize internal whitespace (replace multiple spaces with single space)
    sanitized = re.sub(r'\s+', ' ', sanitized)

    return sanitized


def sanitize_meeting_code(meeting_code: str) -> str:
    """
    Sanitize meeting code input.

    Meeting codes should be alphanumeric and may include hyphens.
    This validates format and prevents injection attacks.

    Args:
        meeting_code: The meeting code to sanitize

    Returns:
        Sanitized meeting code (uppercase, trimmed)

    Raises:
        ValueError: If meeting code is invalid or too long
    """
    if not isinstance(meeting_code, str):
        raise ValueError("Meeting code must be a string")

    # Trim and convert to uppercase for consistency
    sanitized = meeting_code.strip().upper()

    if not sanitized:
        raise ValueError("Meeting code cannot be empty")

    if len(sanitized) > MAX_MEETING_CODE_LENGTH:
        raise ValueError(f"Meeting code exceeds maximum length of {MAX_MEETING_CODE_LENGTH} characters")

    # Allow only alphanumeric characters and hyphens
    if not re.match(r'^[A-Z0-9-]+$', sanitized):
        raise ValueError("Meeting code can only contain letters, numbers, and hyphens")

    return sanitized


def sanitize_poll_name(poll_name: str) -> str:
    """
    Sanitize poll name input.

    Args:
        poll_name: The poll name to sanitize

    Returns:
        Sanitized poll name

    Raises:
        ValueError: If poll name is invalid or too long
    """
    sanitized = sanitize_text(poll_name, max_length=MAX_POLL_NAME_LENGTH)

    if not sanitized:
        raise ValueError("Poll name cannot be empty")

    return sanitized


def validate_token_format(token: str) -> str:
    """
    Validate token format before processing.

    Tokens should be URL-safe base64 strings.
    This prevents malformed tokens from causing unnecessary database queries.

    Args:
        token: The token to validate

    Returns:
        The validated token

    Raises:
        ValueError: If token format is invalid
    """
    if not isinstance(token, str):
        raise ValueError("Token must be a string")

    token = token.strip()

    if not token:
        raise ValueError("Token cannot be empty")

    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError(f"Token exceeds maximum length of {MAX_TOKEN_LENGTH} characters")

    # URL-safe base64 uses: A-Z, a-z, 0-9, -, _
    if not re.match(r'^[A-Za-z0-9_-]+$', token):
        raise ValueError("Token format is invalid (must be URL-safe base64)")

    return token
