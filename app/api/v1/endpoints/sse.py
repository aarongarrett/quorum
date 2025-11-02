"""Server-Sent Events endpoints."""
import asyncio
import json
from typing import Dict
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db_context, TIMEZONE, verify_admin_token
from app.services.meeting import get_available_meetings, get_all_meetings
from app.core.constants import SSE_USER_INTERVAL, SSE_ADMIN_INTERVAL

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
            except Exception as e:
                consecutive_errors += 1

                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"SSE data fetch error (attempt {consecutive_errors}/{max_consecutive_errors}): {e}")

                # Only terminate after multiple consecutive failures
                # This allows recovery from transient database hiccups
                if consecutive_errors >= max_consecutive_errors:
                    yield f"event: error\ndata: {json.dumps({'error': 'Service temporarily unavailable'})}\n\n"
                    break
                # Otherwise, skip this update and retry after the interval

            # Wait before next update
            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        # Client disconnected
        pass


@router.get("/sse/meetings")
async def sse_meetings(request: Request, tokens: str = ""):
    """
    SSE endpoint for available meetings.

    Query params:
        tokens: JSON-encoded token map {meeting_id: token}

    The client should reconnect automatically if disconnected.
    """
    # Parse token map
    try:
        token_map = json.loads(tokens) if tokens else {}
        # Convert string keys to int
        token_map = {int(k): v for k, v in token_map.items()}
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid tokens parameter")

    def get_data():
        with get_db_context() as db:
            return get_available_meetings(db, token_map, TIMEZONE)

    return StreamingResponse(
        event_generator(request, get_data, interval=SSE_USER_INTERVAL),
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
    SSE endpoint for admin meetings view.

    Requires admin authentication via cookie.
    Updates every 3 seconds with full meeting stats.
    The client should reconnect automatically if disconnected.
    """
    def get_data():
        with get_db_context() as db:
            return get_all_meetings(db, TIMEZONE)

    return StreamingResponse(
        event_generator(request, get_data, interval=SSE_ADMIN_INTERVAL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
