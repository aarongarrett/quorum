"""Authentication schemas."""
from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
