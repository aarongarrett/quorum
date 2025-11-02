"""Tests for input sanitization utilities."""
import pytest

from app.core.sanitization import (
    sanitize_text,
    sanitize_meeting_code,
    sanitize_poll_name,
    validate_token_format,
    MAX_MEETING_CODE_LENGTH,
    MAX_POLL_NAME_LENGTH,
    MAX_TOKEN_LENGTH,
)


class TestSanitizeText:
    """Tests for sanitize_text function."""

    def test_sanitize_basic_text(self):
        """Test basic text sanitization."""
        result = sanitize_text("Hello World")
        assert result == "Hello World"

    def test_sanitize_with_html_tags(self):
        """Test that HTML tags are stripped."""
        result = sanitize_text("<script>alert('xss')</script>")
        assert result == "alert('xss')"
        assert "<script>" not in result
        assert "</script>" not in result

    def test_sanitize_with_quotes(self):
        """Test that quotes are preserved (React will handle escaping)."""
        result = sanitize_text('Hello "World"')
        assert result == 'Hello "World"'

    def test_sanitize_with_ampersand(self):
        """Test that ampersands are preserved (React will handle escaping)."""
        result = sanitize_text("A & B")
        assert result == "A & B"

    def test_sanitize_trims_whitespace(self):
        """Test that leading/trailing whitespace is trimmed."""
        result = sanitize_text("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_normalizes_internal_whitespace(self):
        """Test that multiple spaces are normalized to single space."""
        result = sanitize_text("Hello    World")
        assert result == "Hello World"

    def test_sanitize_with_max_length(self):
        """Test that max length is enforced."""
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_text("A" * 100, max_length=50)

    def test_sanitize_empty_string(self):
        """Test empty string after trimming."""
        result = sanitize_text("   ")
        assert result == ""

    def test_sanitize_non_string_raises_error(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_text(123)  # type: ignore

    def test_sanitize_complex_xss_payload(self):
        """Test complex XSS payload is neutralized by stripping tags."""
        payload = '<img src=x onerror="alert(1)">'
        result = sanitize_text(payload)
        # Verify HTML tags are stripped (XSS is neutralized)
        assert "<img" not in result
        assert "</" not in result
        assert ">" not in result
        # Only the content remains
        assert result == ''  # Empty because <img> is self-closing with no content


class TestSanitizeMeetingCode:
    """Tests for sanitize_meeting_code function."""

    def test_sanitize_valid_meeting_code(self):
        """Test valid meeting code is processed correctly."""
        result = sanitize_meeting_code("ABCD1234")
        assert result == "ABCD1234"

    def test_sanitize_lowercase_meeting_code(self):
        """Test lowercase is converted to uppercase."""
        result = sanitize_meeting_code("abcd1234")
        assert result == "ABCD1234"

    def test_sanitize_meeting_code_with_hyphens(self):
        """Test meeting code with hyphens is allowed."""
        result = sanitize_meeting_code("ABCD-1234")
        assert result == "ABCD-1234"

    def test_sanitize_meeting_code_trims_whitespace(self):
        """Test whitespace is trimmed."""
        result = sanitize_meeting_code("  ABCD1234  ")
        assert result == "ABCD1234"

    def test_sanitize_empty_meeting_code(self):
        """Test empty meeting code raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_meeting_code("")

    def test_sanitize_whitespace_only_meeting_code(self):
        """Test whitespace-only meeting code raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_meeting_code("   ")

    def test_sanitize_meeting_code_too_long(self):
        """Test meeting code exceeding max length raises error."""
        long_code = "A" * (MAX_MEETING_CODE_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_meeting_code(long_code)

    def test_sanitize_meeting_code_with_special_chars(self):
        """Test meeting code with invalid characters raises error."""
        with pytest.raises(ValueError, match="can only contain"):
            sanitize_meeting_code("ABCD<script>")

    def test_sanitize_meeting_code_with_spaces(self):
        """Test meeting code with spaces raises error."""
        with pytest.raises(ValueError, match="can only contain"):
            sanitize_meeting_code("ABCD 1234")

    def test_sanitize_meeting_code_with_sql_injection(self):
        """Test meeting code with SQL injection attempt is rejected."""
        with pytest.raises(ValueError, match="can only contain"):
            sanitize_meeting_code("ABCD'; DROP TABLE meetings;--")

    def test_sanitize_meeting_code_non_string(self):
        """Test non-string meeting code raises error."""
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_meeting_code(12345)  # type: ignore


class TestSanitizePollName:
    """Tests for sanitize_poll_name function."""

    def test_sanitize_valid_poll_name(self):
        """Test valid poll name is processed correctly."""
        result = sanitize_poll_name("What is your favorite color?")
        assert result == "What is your favorite color?"

    def test_sanitize_poll_name_with_html(self):
        """Test HTML in poll name is stripped."""
        result = sanitize_poll_name("<b>Important Poll</b>")
        assert result == "Important Poll"
        assert "<b>" not in result
        assert "</b>" not in result

    def test_sanitize_poll_name_trims_whitespace(self):
        """Test whitespace is trimmed."""
        result = sanitize_poll_name("  My Poll  ")
        assert result == "My Poll"

    def test_sanitize_empty_poll_name(self):
        """Test empty poll name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_poll_name("")

    def test_sanitize_whitespace_only_poll_name(self):
        """Test whitespace-only poll name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_poll_name("   ")

    def test_sanitize_poll_name_too_long(self):
        """Test poll name exceeding max length raises error."""
        long_name = "A" * (MAX_POLL_NAME_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_poll_name(long_name)

    def test_sanitize_poll_name_at_max_length(self):
        """Test poll name at exactly max length is allowed."""
        name_at_limit = "A" * MAX_POLL_NAME_LENGTH
        result = sanitize_poll_name(name_at_limit)
        assert result == name_at_limit

    def test_sanitize_poll_name_with_quotes(self):
        """Test quotes are preserved."""
        result = sanitize_poll_name('Poll "Question" Name')
        assert result == 'Poll "Question" Name'

    def test_sanitize_poll_name_with_xss(self):
        """Test XSS payload in poll name is rejected (becomes empty after stripping)."""
        payload = '<img src=x onerror="alert(\'xss\')">'
        # Self-closing tag has no content, so it becomes empty and is rejected
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_poll_name(payload)

    def test_sanitize_poll_name_normalizes_whitespace(self):
        """Test internal whitespace is normalized."""
        result = sanitize_poll_name("Poll   with   spaces")
        assert result == "Poll with spaces"

    def test_sanitize_poll_name_rejects_only_html_tags(self):
        """Test poll name that's only HTML tags is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_poll_name("<div></div>")

    def test_sanitize_poll_name_rejects_malformed_html(self):
        """Test poll name with malformed HTML is rejected."""
        with pytest.raises(ValueError, match="invalid HTML-like patterns"):
            sanitize_poll_name("Poll Name <invalid")

    def test_sanitize_poll_name_rejects_angle_brackets(self):
        """Test poll name with bare angle brackets is rejected."""
        with pytest.raises(ValueError, match="invalid HTML-like patterns"):
            sanitize_poll_name("Poll > Name")


class TestValidateTokenFormat:
    """Tests for validate_token_format function."""

    def test_validate_valid_token(self):
        """Test valid URL-safe base64 token."""
        token = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_"
        result = validate_token_format(token)
        assert result == token

    def test_validate_token_trims_whitespace(self):
        """Test whitespace is trimmed."""
        token = "  ValidToken123  "
        result = validate_token_format(token)
        assert result == "ValidToken123"

    def test_validate_empty_token(self):
        """Test empty token raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_token_format("")

    def test_validate_whitespace_only_token(self):
        """Test whitespace-only token raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_token_format("   ")

    def test_validate_token_too_long(self):
        """Test token exceeding max length raises error."""
        long_token = "A" * (MAX_TOKEN_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_token_format(long_token)

    def test_validate_token_with_invalid_chars(self):
        """Test token with invalid characters raises error."""
        with pytest.raises(ValueError, match="format is invalid"):
            validate_token_format("Token@#$%")

    def test_validate_token_with_spaces(self):
        """Test token with spaces raises error."""
        with pytest.raises(ValueError, match="format is invalid"):
            validate_token_format("Token With Spaces")

    def test_validate_token_with_special_chars(self):
        """Test token with special characters raises error."""
        with pytest.raises(ValueError, match="format is invalid"):
            validate_token_format("Token<script>alert(1)</script>")

    def test_validate_token_non_string(self):
        """Test non-string token raises error."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_token_format(12345)  # type: ignore

    def test_validate_token_allows_underscore_and_hyphen(self):
        """Test token with underscore and hyphen (URL-safe base64)."""
        token = "Valid-Token_123"
        result = validate_token_format(token)
        assert result == token

    def test_validate_token_rejects_plus_and_slash(self):
        """Test token with + and / (standard base64, not URL-safe) is rejected."""
        with pytest.raises(ValueError, match="format is invalid"):
            validate_token_format("Token+With/Slash")
