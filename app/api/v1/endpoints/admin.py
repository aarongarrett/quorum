"""Admin endpoints."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_admin_token, TIMEZONE
from app.schemas import AdminMeetingDetail
from app.services.meeting import get_all_meetings, delete_meeting
from app.services.poll import delete_poll
from app.core.cache import global_cache

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_token)])


@router.get("/meetings", response_model=List[AdminMeetingDetail])
async def get_all_meetings_endpoint(db: Session = Depends(get_db)):
    """
    Get all meetings with full details (admin only).

    Uses caching with 3-second TTL to reduce database load.
    """
    try:
        meetings = get_all_meetings(db, TIMEZONE, cache=global_cache)
        return meetings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/meetings/{meeting_id}")
async def delete_meeting_endpoint(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a meeting (admin only).

    Cache invalidation:
        - Invalidates both base_meetings and admin_all_meetings caches
        - Ensures SSE clients see deletion instantly
    """
    success = delete_meeting(db, meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Invalidate caches for instant updates
    logger.info(f"Cache invalidated: base_meetings, admin_all_meetings (reason: meeting deleted, meeting_id={meeting_id})")
    global_cache.invalidate("base_meetings")
    global_cache.invalidate("admin_all_meetings")

    return {"success": True}


@router.delete("/meetings/{meeting_id}/polls/{poll_id}")
async def delete_poll_endpoint(
    meeting_id: int,
    poll_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a poll (admin only).

    Cache invalidation:
        - Invalidates both base_meetings and admin_all_meetings caches
        - Ensures SSE clients see deletion instantly
    """
    try:
        delete_poll(db, meeting_id, poll_id)

        # Invalidate caches for instant updates
        logger.info(f"Cache invalidated: base_meetings, admin_all_meetings (reason: poll deleted, poll_id={poll_id}, meeting_id={meeting_id})")
        global_cache.invalidate("base_meetings")
        global_cache.invalidate("admin_all_meetings")

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for monitoring (admin only).

    Returns cache metrics including:
    - size: Current number of cached entries
    - max_size: Maximum cache capacity
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate_percent: Cache hit rate percentage
    - entries: Details of each cached entry
    """
    return global_cache.get_stats()
