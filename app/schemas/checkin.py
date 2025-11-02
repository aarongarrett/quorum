"""Check-in schemas."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_meeting_code, validate_token_format


class CheckinRequest(BaseModel):
    meeting_code: str = Field(..., min_length=1, max_length=50)
    token: Optional[str] = Field(None, max_length=100)  # For re-check-in with existing token

    @field_validator('meeting_code')
    @classmethod
    def sanitize_meeting_code_field(cls, v: str) -> str:
        """Sanitize and validate meeting code."""
        return sanitize_meeting_code(v)

    @field_validator('token')
    @classmethod
    def validate_token_field(cls, v: Optional[str]) -> Optional[str]:
        """Validate token format if provided."""
        if v is not None:
            return validate_token_format(v)
        return v


class CheckinResponse(BaseModel):
    token: str
