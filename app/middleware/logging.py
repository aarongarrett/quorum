"""Logging middleware for request tracking."""
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with request IDs."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store request ID in request.state for access in endpoint handlers
        request.state.request_id = request_id

        # Add request ID to context vars (available to all logs in this request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Start timer
        start_time = time.time()

        # Log incoming request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                exception=str(exc),
                exception_type=type(exc).__name__,
                duration_ms=round(duration * 1000, 2),
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log completed request
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        return response
