"""Vote schemas."""
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import validate_token_format


class VoteRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=100)
    vote: str = Field(..., min_length=1, max_length=1, pattern="^[A-H]$")

    @field_validator('token')
    @classmethod
    def validate_token_field(cls, v: str) -> str:
        """Validate token format."""
        return validate_token_format(v)
