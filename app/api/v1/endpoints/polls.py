"""Poll endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token
from app.schemas import PollCreate, PollResponse, VoteRequest, VoteResponse
from app.services.poll import create_poll
from app.services.vote import vote_in_poll
from app.core.rate_limit import limiter, RATE_LIMITS

router = APIRouter()


@router.post("/meetings/{meeting_id}/polls", response_model=PollResponse, dependencies=[Depends(verify_admin_token)])
async def create_poll_endpoint(
    meeting_id: int,
    poll: PollCreate,
    db: Session = Depends(get_db)
):
    """Create a new poll in a meeting (admin only)."""
    try:
        poll_id = create_poll(db, meeting_id, poll.name)
        # SSE clients will receive the update on their next polling interval
        return PollResponse(poll_id=poll_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meetings/{meeting_id}/polls/{poll_id}/votes", response_model=VoteResponse)
@limiter.limit(RATE_LIMITS["vote"])
async def vote_endpoint(
    request: Request,
    meeting_id: int,
    poll_id: int,
    vote_request: VoteRequest,
    db: Session = Depends(get_db)
):
    """Cast a vote in a poll."""
    try:
        vote_in_poll(db, meeting_id, poll_id, vote_request.token, vote_request.vote)
        return VoteResponse(success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
