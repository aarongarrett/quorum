"""Application constants.

This module contains magic strings and numbers used throughout the application.
Centralizing these values makes them easier to maintain and modify.
"""

# Vote Options
# Available voting options for polls (A through H = 8 options)
VOTE_OPTIONS = "ABCDEFGH"
MAX_VOTE_OPTIONS = len(VOTE_OPTIONS)

# Server-Sent Events (SSE) Configuration
# NOTE: SSE intervals have been moved to app.core.config.Settings
# This allows environment variable override (e.g., SSE_USER_INTERVAL=10)
# Import from settings instead: from app.core.config import settings

# Meeting Code Configuration
# Meeting codes are 8-character alphanumeric strings
MEETING_CODE_LENGTH = 8

# JWT Token Configuration
# Token expiration time in minutes (8 hours)
ACCESS_TOKEN_EXPIRE_MINUTES = 480
