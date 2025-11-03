"""Poll endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token
from app.schemas import PollCreate, PollResponse, VoteRequest, SuccessResponse
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
    Create a new poll in an existing meeting (admin only).

    This endpoint creates a poll within a meeting that users can vote on.
    Poll names are sanitized to prevent special characters. Vote options
    are A-H by default (configurable in schemas/vote.py). Requires admin
    authentication via JWT cookie.

    Args:
        meeting_id: ID of the meeting to add poll to
        poll: PollCreate schema with poll name
        db: Database session (injected)

    Returns:
        PollResponse containing the created poll_id

    Raises:
        HTTPException: 400 if meeting doesn't exist or poll name is invalid
        HTTPException: 401 if not authenticated as admin

    Example:
        Request:
            POST /api/v1/meetings/42/polls
            Cookie: admin_token=eyJhbGc...
            {
                "name": "Approve budget for Q1"
            }

        Response (200):
            {
                "poll_id": 15
            }

        Response (400):
            {
                "detail": "Meeting does not exist"
            }

    Cache Invalidation:
        - Invalidates base_meetings cache (user SSE stream)
        - Invalidates admin_all_meetings cache (admin SSE stream)
        - Ensures SSE clients see new poll instantly
        - Without invalidation, would take up to 3 seconds (cache TTL)

    Note:
        Poll names are sanitized by removing special characters and limiting
        length to prevent display issues and potential injection attacks.
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


@router.post("/meetings/{meeting_id}/polls/{poll_id}/votes", response_model=SuccessResponse)
@limiter.limit(RATE_LIMITS["vote"])
async def vote_endpoint(
    request: Request,
    meeting_id: int,
    poll_id: int,
    vote_request: VoteRequest,
    db: Session = Depends(get_db)
) -> SuccessResponse:
    """
    Cast or update a vote in a poll using a check-in token.

    This endpoint allows checked-in users to vote on a poll. Users must provide
    their vote token obtained during check-in. Votes can be changed by calling
    this endpoint again with the same token and a different vote value.

    Args:
        request: FastAPI Request (for rate limiting)
        meeting_id: ID of the meeting containing the poll
        poll_id: ID of the poll to vote in
        vote_request: VoteRequest with token and vote (A-H)
        db: Database session (injected)

    Returns:
        SuccessResponse with success status

    Raises:
        HTTPException: 400 if token invalid, poll doesn't exist, or vote invalid

    Rate Limit:
        200 requests per minute per IP

    Example:
        Request:
            POST /api/v1/meetings/42/polls/15/votes
            {
                "token": "abc123def456...",
                "vote": "A"
            }

        Response (200):
            {
                "success": true,
                "message": null
            }

        Response (400):
            {
                "detail": "Invalid token"
            }

        Response (400):
            {
                "detail": "You have already voted in this poll"
            }

    Vote Values:
        - Valid votes: A, B, C, D, E, F, G, H (default)
        - Configurable in schemas/vote.py
        - Pattern validated: ^[A-H]$

    Security:
        - Token must match Argon2 hash stored during check-in
        - Duplicate votes prevented by unique constraint
        - Vote updates allowed (changes vote, doesn't create duplicate)
        - Token cannot be used across different meetings

    Note:
        Votes are stored with meeting_id, poll_id, and hashed token.
        The unique constraint on (poll_id, token_lookup_key) prevents
        duplicate votes while allowing vote changes.
    """
    try:
        vote_in_poll(db, meeting_id, poll_id, vote_request.token, vote_request.vote)
        return SuccessResponse(success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
