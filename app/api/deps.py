"""Shared API dependencies."""
from typing import Generator
from zoneinfo import ZoneInfo
import os
from sqlalchemy.orm import Session

from app.db import get_db, get_db_context
from app.core.security import verify_admin_token

# Timezone configuration
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "America/New_York"))

__all__ = ["get_db", "get_db_context", "verify_admin_token", "TIMEZONE"]
