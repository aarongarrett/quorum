"""Admin endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token, TIMEZONE
from app.schemas import AdminMeetingDetail
from app.services.meeting import get_all_meetings, delete_meeting
from app.services.poll import delete_poll

router = APIRouter(dependencies=[Depends(verify_admin_token)])


@router.get("/meetings", response_model=List[AdminMeetingDetail])
async def get_all_meetings_endpoint(db: Session = Depends(get_db)):
    """Get all meetings with full details (admin only)."""
    try:
        meetings = get_all_meetings(db, TIMEZONE)
        return meetings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/meetings/{meeting_id}")
async def delete_meeting_endpoint(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Delete a meeting (admin only)."""
    success = delete_meeting(db, meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"success": True}


@router.delete("/meetings/{meeting_id}/polls/{poll_id}")
async def delete_poll_endpoint(
    meeting_id: int,
    poll_id: int,
    db: Session = Depends(get_db)
):
    """Delete a poll (admin only)."""
    try:
        delete_poll(db, meeting_id, poll_id)
        # SSE clients will receive the update on their next polling interval
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
