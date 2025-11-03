"""Server-Sent Events endpoints."""
import asyncio
import json
import logging
from typing import Dict
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, DatabaseError

from app.api.deps import get_db_context, TIMEZONE, verify_admin_token
from app.services.meeting import get_available_meetings, get_all_meetings
from app.core.config import settings
from app.core.cache import global_cache

logger = logging.getLogger(__name__)
router = APIRouter()


async def event_generator(request: Request, data_func, interval: int = 5):
    """
    Generic SSE event generator.

    Args:
        request: FastAPI request object to check for client disconnect
        data_func: Function that returns the data to send
        interval: Seconds between updates
    """
    consecutive_errors = 0
    max_consecutive_errors = 3  # Terminate after 3 consecutive failures

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Get data and send as SSE event
            try:
                data = data_func()
                yield f"data: {json.dumps(data)}\n\n"
                consecutive_errors = 0  # Reset error counter on success
            except (SQLAlchemyError, DatabaseError) as e:
                # Database errors - expected, can retry
                consecutive_errors += 1
                logger.warning(f"SSE database error (attempt {consecutive_errors}/{max_consecutive_errors}): {e}")

                # Only terminate after multiple consecutive failures
                # This allows recovery from transient database hiccups
                if consecutive_errors >= max_consecutive_errors:
                    yield f"event: error\ndata: {json.dumps({'error': 'Service temporarily unavailable'})}\n\n"
                    break
                # Otherwise, skip this update and retry after the interval
            except Exception as e:
                # Unexpected errors (AttributeError, KeyError, etc.) - log full trace and terminate
                logger.exception(f"SSE unexpected error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': 'Internal error'})}\n\n"
                break

            # Wait before next update
            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        # Client disconnected
        pass


@router.get("/sse/meetings")
async def sse_meetings(request: Request, tokens: str = ""):
    """
    SSE endpoint for available meetings (with two-tier caching).

    Query params:
        tokens: JSON-encoded token map {meeting_id: token}

    Caching strategy:
        - TIER 1: Shared base meeting data (3-second TTL, cached globally)
        - TIER 2: User-specific check-in/vote data (not cached, fast indexed queries)

    The client should reconnect automatically if disconnected.
    """
    # Parse token map
    try:
        token_map = json.loads(tokens) if tokens else {}
        # Convert string keys to int
        token_map = {int(k): v for k, v in token_map.items()}
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid tokens parameter")

    def get_data():
        with get_db_context() as db:
            # Pass global cache to enable two-tier caching
            return get_available_meetings(db, token_map, TIMEZONE, cache=global_cache)

    return StreamingResponse(
        event_generator(request, get_data, interval=settings.SSE_USER_INTERVAL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


@router.get("/sse/admin/meetings")
async def sse_admin_meetings(request: Request, admin: dict = Depends(verify_admin_token)):
    """
    SSE endpoint for admin meetings view (with caching).

    Requires admin authentication via cookie.
    Updates every 3 seconds with full meeting stats.

    Caching strategy:
        - TTL: 3 seconds
        - Cache key: "admin_all_meetings"
        - Shared globally (though typically only 1 admin connection)
        - Maintains consistency with user endpoint caching

    The client should reconnect automatically if disconnected.
    """
    def get_data():
        with get_db_context() as db:
            # Pass global cache to enable caching
            return get_all_meetings(db, TIMEZONE, cache=global_cache)

    return StreamingResponse(
        event_generator(request, get_data, interval=settings.SSE_ADMIN_INTERVAL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
