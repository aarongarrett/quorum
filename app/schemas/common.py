"""Common response schemas."""
from pydantic import BaseModel
from typing import Optional


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response for documentation."""
    success: bool = False
    error: ErrorDetail
