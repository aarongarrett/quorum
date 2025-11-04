"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from app.api.v1.router import api_router
from app.api.deps import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging_config import setup_logging, get_logger
from app.core.cache import global_cache
from app.middleware import LoggingMiddleware

# Initialize structured logging
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger(__name__)

# Validate production configuration after logging is configured
# This ensures settings.ENVIRONMENT can be safely accessed and properly reads from .env or env vars
if settings.ENVIRONMENT == "production":
    settings.validate_production_config()

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

# Add API versioning middleware
@app.middleware("http")
async def add_api_version_header(request: Request, call_next):
    """Add X-API-Version header to all responses for version tracking."""
    response = await call_next(request)
    response.headers["X-API-Version"] = settings.APP_VERSION
    return response

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

# Health endpoint - must be defined before catch-all route
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with comprehensive metrics.

    Returns:
        - status: "healthy" or "unhealthy"
        - cache: Cache statistics (size, hits, misses, hit rate)
        - database: Database connection status and pool metrics
        - memory: Memory usage statistics
        - environment: Current environment setting

    Returns 503 if database is unreachable.
    """
    from app.db.session import engine

    health_status = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "cache": global_cache.get_stats(),
        "database": {
            "status": "connected",
            "pool": {
                "size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "total_connections": engine.pool.checkedout() + engine.pool.checkedin(),
            }
        }
    }

    # Try to get memory usage if psutil is available (cross-platform)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        health_status["memory"] = {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2),
        }
    except ImportError:
        # psutil not available, skip memory metrics
        health_status["memory"] = {"status": "psutil not installed"}
    except Exception as e:
        logger.warning("health_check_memory_error", error=str(e))
        health_status["memory"] = {"error": "unable to read"}

    try:
        # Test database connection with a simple query
        db.execute(text("SELECT 1"))
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"]["status"] = f"error: {str(e)}"
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

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
