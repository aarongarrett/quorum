"""Meeting endpoints."""
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

router = APIRouter()


@router.post("", response_model=MeetingResponse, dependencies=[Depends(verify_admin_token)])
async def create_meeting_endpoint(
    meeting: MeetingCreate,
    db: Session = Depends(get_db)
):
    """Create a new meeting (admin only)."""
    try:
        meeting_id, meeting_code = create_meeting(db, meeting.start_time, meeting.end_time)
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
    """Get available meetings with check-in/vote status. Token map: {meeting_id: token}"""
    try:
        meetings = get_available_meetings(db, token_map, TIMEZONE)
        return meetings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{meeting_id}/checkins", response_model=CheckinResponse)
@limiter.limit(RATE_LIMITS["check_in"])
async def checkin_endpoint(
    request: Request,
    meeting_id: int,
    checkin_request: CheckinRequest,
    db: Session = Depends(get_db)
):
    """Check in to a meeting. Provide existing token to get same token back (idempotent)."""
    try:
        token = checkin(db, meeting_id, checkin_request.meeting_code, checkin_request.token)
        return CheckinResponse(token=token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
