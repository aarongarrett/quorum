"""Application constants.

This module contains magic strings and numbers used throughout the application.
Centralizing these values makes them easier to maintain and modify.
"""

# Vote Options
# Available voting options for polls (A through H = 8 options)
VOTE_OPTIONS = "ABCDEFGH"
MAX_VOTE_OPTIONS = len(VOTE_OPTIONS)

# Server-Sent Events (SSE) Configuration
# How often to send updates to clients (in seconds)
SSE_USER_INTERVAL = 5  # User-facing meeting list updates every 5 seconds
SSE_ADMIN_INTERVAL = 3  # Admin dashboard updates every 3 seconds (faster for real-time monitoring)

# Meeting Code Configuration
# Meeting codes are 8-character alphanumeric strings
MEETING_CODE_LENGTH = 8

# JWT Token Configuration
# Token expiration time in minutes (8 hours)
ACCESS_TOKEN_EXPIRE_MINUTES = 480
