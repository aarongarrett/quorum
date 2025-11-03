"""Poll endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token
from app.schemas import PollCreate, PollResponse, VoteRequest, VoteResponse
from app.services.poll import create_poll
from app.services.vote import vote_in_poll
from app.core.rate_limit import limiter, RATE_LIMITS
from app.core.cache import global_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/meetings/{meeting_id}/polls", response_model=PollResponse, dependencies=[Depends(verify_admin_token)])
async def create_poll_endpoint(
    meeting_id: int,
    poll: PollCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new poll in a meeting (admin only).

    Cache invalidation:
        - Invalidates both base_meetings and admin_all_meetings caches
        - Ensures SSE clients see new poll instantly
        - Without invalidation, would take up to 3 seconds (cache TTL)
    """
    try:
        poll_id = create_poll(db, meeting_id, poll.name)

        # Invalidate caches for instant updates
        logger.info(f"Cache invalidated: base_meetings, admin_all_meetings (reason: poll created, poll_id={poll_id}, meeting_id={meeting_id})")
        global_cache.invalidate("base_meetings")
        global_cache.invalidate("admin_all_meetings")

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
