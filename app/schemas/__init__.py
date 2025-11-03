"""Pydantic schemas for request/response validation."""
from app.schemas.auth import AdminLoginRequest, AdminLoginResponse
from app.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
    MeetingDetail,
    AvailableMeeting,
    AdminMeetingDetail,
)
from app.schemas.poll import PollCreate, PollResponse, PollDetail, PollWithVote
from app.schemas.checkin import CheckinRequest, CheckinResponse
from app.schemas.vote import VoteRequest
from app.schemas.common import SuccessResponse, ErrorResponse, ErrorDetail

__all__ = [
    "AdminLoginRequest",
    "AdminLoginResponse",
    "MeetingCreate",
    "MeetingResponse",
    "MeetingDetail",
    "AvailableMeeting",
    "AdminMeetingDetail",
    "PollCreate",
    "PollResponse",
    "PollDetail",
    "PollWithVote",
    "CheckinRequest",
    "CheckinResponse",
    "VoteRequest",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
]
