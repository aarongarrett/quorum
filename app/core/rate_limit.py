"""Rate limiting configuration."""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request):
    """Get client IP for rate limiting, considering proxies."""
    # Check X-Forwarded-For header (from reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded.split(",")[0].strip()

    # Fall back to direct connection IP
    return get_remote_address(request)


# Create rate limiter instance
# Uses Redis if REDIS_URL is set (Docker/production), falls back to memory for local dev
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["100/minute"],  # Global default
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    strategy="fixed-window"
)

# Rate limit definitions for different endpoint categories
# Note: Campus WiFi environments may share public IPs via NAT,
# so limits are set to accommodate ~200 concurrent users
RATE_LIMITS = {
    # Public endpoints (designed for campus WiFi with shared IPs)
    "check_in": "200/minute",  # Allow rapid check-ins for large meetings
    "vote": "200/minute",  # Allow concurrent voting from many users
    "available_meetings": "200/minute",  # Listing endpoint

    # Admin endpoints (less restrictive)
    "admin_read": "200/minute",
    "admin_write": "200/minute",
}
