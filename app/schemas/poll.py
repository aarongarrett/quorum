"""Poll schemas."""
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_poll_name


class PollCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)

    @field_validator('name')
    @classmethod
    def sanitize_name_field(cls, v: str) -> str:
        """Sanitize and validate poll name."""
        return sanitize_poll_name(v)


class PollResponse(BaseModel):
    poll_id: int


class PollDetail(BaseModel):
    id: int
    name: str
    total_votes: int
    votes: Dict[str, int]


class PollWithVote(BaseModel):
    id: int
    name: str
    vote: Optional[str] = None
