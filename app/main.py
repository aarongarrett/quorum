"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging_config import setup_logging, get_logger
from app.middleware import LoggingMiddleware

# Initialize structured logging
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger(__name__)

logger.info(
    "application_starting",
    app_title=settings.APP_TITLE,
    app_version=settings.APP_VERSION,
    environment=settings.ENVIRONMENT,
)

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
)

# Add rate limiter to app state
app.state.limiter = limiter

# Add rate limit exceeded exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add logging middleware (must be added before other middleware for proper request tracking)
app.add_middleware(LoggingMiddleware)

# CORS middleware - configured for cookie-based auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Configured via environment
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Serve React static files in production
if os.path.exists(settings.FRONTEND_BUILD_PATH):
    # Vite uses 'assets' directory instead of 'static'
    assets_path = f"{settings.FRONTEND_BUILD_PATH}/assets"
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/", response_class=FileResponse)
    async def serve_root():
        """Serve React app root."""
        return FileResponse(f"{settings.FRONTEND_BUILD_PATH}/index.html")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        """Serve React app for all non-API routes."""
        # Don't serve API routes as React app
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not found")

        # Try to serve static file first
        file_path = f"{settings.FRONTEND_BUILD_PATH}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Otherwise serve index.html (for React Router)
        return FileResponse(f"{settings.FRONTEND_BUILD_PATH}/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
