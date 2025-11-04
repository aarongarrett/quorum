"""Meeting endpoints."""
import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token, TIMEZONE
from app.schemas import (
    MeetingCreate,
    MeetingResponse,
    AvailableMeeting,
    CheckinRequest,
    CheckinResponse,
)
from app.services.meeting import create_meeting, get_available_meetings
from app.services.checkin import checkin
from app.core.rate_limit import limiter, RATE_LIMITS
from app.core.cache import global_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=MeetingResponse, dependencies=[Depends(verify_admin_token)])
async def create_meeting_endpoint(
    meeting: MeetingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new meeting with automatically generated meeting code (admin only).

    This endpoint creates a new meeting with specified start and end times. It
    generates a unique, pronounceable meeting code (e.g., "TOXEVIMA") for users
    to check in. Requires admin authentication via JWT cookie.

    Args:
        meeting: MeetingCreate schema with start_time and end_time (ISO 8601)
        db: Database session (injected)

    Returns:
        MeetingResponse containing meeting_id and generated meeting_code

    Raises:
        HTTPException: 400 if validation fails (invalid times, end before start)
        HTTPException: 401 if not authenticated as admin

    Example:
        Request:
            POST /api/v1/meetings
            Cookie: admin_token=eyJhbGc...
            {
                "start_time": "2025-11-03T15:00:00Z",
                "end_time": "2025-11-03T16:00:00Z"
            }

        Response (200):
            {
                "meeting_id": 42,
                "meeting_code": "TOXEVIMA"
            }

        Response (400):
            {
                "detail": "End time must be after start time"
            }

    Cache Invalidation:
        - Invalidates base_meetings cache (user SSE stream)
        - Invalidates admin_all_meetings cache (admin SSE stream)
        - Ensures SSE clients see new meeting within ~1 second
        - Without invalidation, would take up to 3 seconds (cache TTL)

    Note:
        Meeting codes are generated using a pronounceable algorithm that
        alternates consonants and vowels for easy verbal communication.
    """
    try:
        meeting_id, meeting_code = create_meeting(db, meeting.start_time, meeting.end_time)

        # Invalidate caches for instant updates
        logger.info(f"Cache invalidated: base_meetings, admin_all_meetings (reason: meeting created, meeting_id={meeting_id})")
        global_cache.invalidate("base_meetings")
        global_cache.invalidate("admin_all_meetings")

        return MeetingResponse(meeting_id=meeting_id, meeting_code=meeting_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/available", response_model=List[AvailableMeeting])
@limiter.limit(RATE_LIMITS["available_meetings"])
async def get_available_meetings_endpoint(
    request: Request,
    token_map: Dict[int, str],
    db: Session = Depends(get_db)
):
    """
    Get list of currently available meetings with user's check-in and vote status.

    This endpoint returns all meetings that are currently in progress (based on
    system timezone) along with the user's check-in status and any polls they
    can vote on. Clients should call this initially and then rely on SSE for
    updates.

    Args:
        request: FastAPI Request (for rate limiting)
        token_map: Dictionary mapping meeting_id to user's vote token
                   Example: {1: "abc123token", 2: "def456token"}
        db: Database session (injected)

    Returns:
        List[AvailableMeeting]: List of available meetings with:
            - id: Meeting ID
            - start_time: Meeting start (ISO 8601)
            - end_time: Meeting end (ISO 8601)
            - meeting_code: Code for check-in (e.g., "TOXEVIMA")
            - checked_in: Boolean indicating if user is checked in
            - polls: List of polls with vote status

    Rate Limit:
        200 requests per minute per IP

    Example:
        Request:
            POST /api/v1/meetings/available
            {
                "1": "abc123token",
                "2": "def456token"
            }

        Response (200):
            [
                {
                    "id": 1,
                    "start_time": "2025-11-03T15:00:00Z",
                    "end_time": "2025-11-03T16:00:00Z",
                    "meeting_code": "TOXEVIMA",
                    "checked_in": true,
                    "polls": [
                        {
                            "id": 10,
                            "name": "Approve budget",
                            "vote": "A"
                        },
                        {
                            "id": 11,
                            "name": "Select venue",
                            "vote": null
                        }
                    ]
                }
            ]

    Note:
        - Only returns meetings currently in progress (now between start and end)
        - checked_in is true only if provided token is valid for that meeting
        - vote field is null if user hasn't voted yet, otherwise shows their vote
        - Timezone is configured via TIMEZONE environment variable
    """
    try:
        meetings = get_available_meetings(db, token_map, TIMEZONE)
        return meetings
    except Exception as e:
        logger.exception(f"Error retrieving available meetings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{meeting_id}/checkins", response_model=CheckinResponse)
@limiter.limit(RATE_LIMITS["check_in"])
async def checkin_endpoint(
    request: Request,
    meeting_id: int,
    checkin_request: CheckinRequest,
    db: Session = Depends(get_db)
):
    """
    Check in to a meeting and receive a vote token (idempotent operation).

    This endpoint allows users to check in to a meeting by providing the correct
    meeting code. On successful check-in, a unique vote token is returned. If the
    user provides their existing token, the same token is returned (idempotent),
    solving the "lost token" problem.

    Args:
        request: FastAPI Request (for rate limiting)
        meeting_id: ID of the meeting to check in to
        checkin_request: CheckinRequest with meeting_code and optional token
        db: Database session (injected)

    Returns:
        CheckinResponse containing the vote token

    Raises:
        HTTPException: 400 if meeting_code is invalid or meeting doesn't exist

    Rate Limit:
        200 requests per minute per IP

    Example:
        Request (first check-in):
            POST /api/v1/meetings/42/checkins
            {
                "meeting_code": "TOXEVIMA",
                "token": null
            }

        Response (200):
            {
                "token": "abc123def456..."
            }

        Request (re-check-in with existing token):
            POST /api/v1/meetings/42/checkins
            {
                "meeting_code": "TOXEVIMA",
                "token": "abc123def456..."
            }

        Response (200):
            {
                "token": "abc123def456..."  // Same token returned
            }

        Response (400):
            {
                "detail": "Invalid meeting code"
            }

    Idempotency:
        - If user provides valid existing token: returns same token
        - If user provides invalid/null token: generates new token
        - Solves "lost token" problem: users can safely re-check-in
        - Token is stored as Argon2 hash for security

    Security:
        - Tokens are 32-byte random URL-safe strings
        - Stored as Argon2 hashes in database
        - Lookup uses HMAC-SHA256 for O(1) performance
        - Meeting code prevents unauthorized check-ins
    """
    try:
        token = checkin(db, meeting_id, checkin_request.meeting_code, checkin_request.token)
        return CheckinResponse(token=token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
